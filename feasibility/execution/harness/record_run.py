#!/usr/bin/env python3
"""record_run.py — write a structured run-log record (schema avrxpu-run/1).

Parses a gem5 stats.txt (+ the per-mnemonic avr_opmix.txt the AVR CPU emits) and
run metadata; emits results/<category>/<workload>/<run_id>.json, retains the raw
stats + op-mix, and — for runs that actually worked (clean exit AND trace match)
— archives the ELF under results/.../elf/<sha>.elf keyed by its sha256. Failing
runs are recorded too, but their ELF is NOT kept. See results/README.md.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

# gem5 stat name -> record key
METRIC_KEYS = {
    "simInsts": "simInsts",
    "simOps": "simOps",
    "system.cpu.numCycles": "numCycles",
    "system.cpu.cpi": "cpi",
    "system.cpu.ipc": "ipc",
    "system.cpu.commitStats0.numIntInsts": "numIntInsts",
    "system.cpu.commitStats0.numLoadInsts": "numLoadInsts",
    "system.cpu.commitStats0.numStoreInsts": "numStoreInsts",
    "system.cpu.commitStats0.numMemRefs": "numMemRefs",
}


def parse_stats(path):
    metrics = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"^(\S+)\s+([-\d.eE]+)", line)
            if not m:
                continue
            name, val = m.group(1), m.group(2)
            try:
                num = int(val)
            except ValueError:
                try:
                    num = float(val)
                except ValueError:
                    continue
            if name in METRIC_KEYS:
                metrics[METRIC_KEYS[name]] = num
    return metrics


def parse_opmix(path):
    """avr_opmix.txt: '<mnemonic> <count>' lines, '#' comments. Returns dict."""
    histo = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                histo[parts[0]] = int(parts[1])
    return histo


def sha256(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--workload", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--kernel", default="")
    p.add_argument("--kind", default="measurement")
    p.add_argument("--stats", required=True)
    p.add_argument("--opmix", default="", help="avr_opmix.txt (default: sibling of --stats)")
    p.add_argument("--elf", default="")
    p.add_argument("--iters", type=int, default=1)
    p.add_argument("--trace", action="store_true")
    p.add_argument("--mcu", default="")
    p.add_argument("--cflags", default="-O1 -ffp-contract=off -fno-fast-math")
    p.add_argument("--toolchain", default="avr-gcc 7.3.0")
    p.add_argument("--gem5-sha", default="")
    p.add_argument("--gem5-dirty", action="store_true")
    p.add_argument("--runner", default="navrobotec")
    p.add_argument("--host-crc", default="")
    p.add_argument("--gem5-crc", default="")
    p.add_argument("--checkpoints", type=int, default=0)
    p.add_argument("--exit-cause", default="")
    p.add_argument("--trace-cmp", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--results", required=True, help="results/ root dir")
    p.add_argument("--no-store-elf", action="store_true",
                   help="never archive the ELF (default: archive iff the run is valid)")
    p.add_argument("--now", default="", help="override UTC timestamp (ISO)")
    a = p.parse_args(argv)

    metrics = parse_stats(a.stats)
    opmix_path = a.opmix or os.path.join(os.path.dirname(a.stats) or ".", "avr_opmix.txt")
    histo = parse_opmix(opmix_path) if os.path.exists(opmix_path) else {}

    now = a.now or datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    stamp = now.replace("-", "").replace(":", "")
    sha8 = (a.gem5_sha or "nogit")[:8]
    run_id = f"{a.workload}_{stamp}_{sha8}_i{a.iters}"
    elf_sha = sha256(a.elf)
    match = bool(a.host_crc) and a.host_crc == a.gem5_crc
    exit_ok = a.exit_cause == "AVR Syscall Exit"
    valid = exit_ok and match

    outdir = os.path.join(a.results, a.category, a.workload)
    os.makedirs(outdir, exist_ok=True)

    # Archive the ELF ONLY for runs that worked (keyed by sha for dedup).
    elf_archived = None
    if valid and a.elf and elf_sha and not a.no_store_elf:
        elfdir = os.path.join(outdir, "elf")
        os.makedirs(elfdir, exist_ok=True)
        dest = os.path.join(elfdir, elf_sha[:12] + ".elf")
        if not os.path.exists(dest):
            shutil.copyfile(a.elf, dest)
        elf_archived = os.path.relpath(dest, a.results)

    rec = {
        "schema": "avrxpu-run/1",
        "run_id": run_id,
        "workload": {"id": a.workload, "category": a.category, "kernel": a.kernel},
        "kind": a.kind,
        "created_utc": now,
        "platform": {"runner": a.runner, "gem5_git": a.gem5_sha, "gem5_dirty": a.gem5_dirty},
        "build": {
            "mcu": a.mcu, "toolchain": a.toolchain, "cflags": a.cflags,
            "iters": a.iters, "trace": a.trace,
            "elf": os.path.basename(a.elf), "elf_sha256": elf_sha,
            "elf_archived": elf_archived,  # null if the run failed (ELF not kept)
        },
        "validation": {
            "host_crc": a.host_crc, "gem5_crc": a.gem5_crc,
            "checkpoints": a.checkpoints, "match": match,
        },
        "exit": {"cause": a.exit_cause, "ok": exit_ok},
        "metrics": metrics,
        "opmix": {
            "available": bool(histo),
            "total": sum(histo.values()) if histo else 0,
            "classes": dict(sorted(histo.items(), key=lambda kv: -kv[1])),
        },
        "raw": {
            "stats": f"{run_id}.stats.txt",
            "opmix": f"{run_id}.opmix.txt" if histo else None,
            "trace_cmp": a.trace_cmp,
        },
        "notes": a.notes,
    }

    with open(os.path.join(outdir, run_id + ".json"), "w") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")
    shutil.copyfile(a.stats, os.path.join(outdir, run_id + ".stats.txt"))
    if histo:
        shutil.copyfile(opmix_path, os.path.join(outdir, run_id + ".opmix.txt"))

    top = list(rec["opmix"]["classes"].items())[:3]
    print(f"recorded {run_id}  valid={valid}  simInsts={metrics.get('simInsts')}  "
          f"cycles={metrics.get('numCycles')}  opmix={'yes' if histo else 'no'} "
          f"top={top}  elf_archived={'yes' if elf_archived else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
