#!/usr/bin/env python3
"""record_run.py — write a structured run-log record (schema avrxpu-run/1).

Parses a gem5 stats.txt + run metadata, emits results/<category>/<workload>/<run_id>.json,
and retains the raw stats.txt alongside it. See results/README.md for the model.

Example:
  record_run.py --workload 11-ekf --category cat1-estimation-control \\
    --kernel "EKF covariance predict (states 0..12)" \\
    --stats m5out/stats.txt --elf ekf_avr.elf --iters 1 --mcu atmega1284p \\
    --gem5-sha 587f9d61b9 --runner navrobotec \\
    --host-crc 26175af3 --gem5-crc 26175af3 --checkpoints 91 \\
    --exit-cause "AVR Syscall Exit" --results /path/to/results
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
    "system.cpu.commitStats0.numFpInsts": "numFpInsts",
}


def parse_stats(path):
    metrics, opmix = {}, {}
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
                    continue  # not a plain number (e.g. a bare 'E') — skip
            if name in METRIC_KEYS:
                metrics[METRIC_KEYS[name]] = num
            cm = re.match(r"^system\.cpu\.commitStats0\.committedInstType::(\S+)", name)
            if cm and num:  # only keep nonzero op-class buckets
                opmix[cm.group(1)] = int(num)
    return metrics, opmix


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
    p.add_argument("--now", default="", help="override UTC timestamp (ISO); else system clock")
    a = p.parse_args(argv)

    metrics, opmix = parse_stats(a.stats)
    now = a.now or datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    stamp = now.replace("-", "").replace(":", "").replace("Z", "Z")
    sha8 = (a.gem5_sha or "nogit")[:8]
    run_id = f"{a.workload}_{stamp}_{sha8}_i{a.iters}"

    match = bool(a.host_crc) and a.host_crc == a.gem5_crc
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
            "elf": os.path.basename(a.elf), "elf_sha256": sha256(a.elf),
        },
        "validation": {
            "host_crc": a.host_crc, "gem5_crc": a.gem5_crc,
            "checkpoints": a.checkpoints, "match": match,
        },
        "exit": {"cause": a.exit_cause, "ok": a.exit_cause == "AVR Syscall Exit"},
        "metrics": metrics,
        "opmix": {
            "available": bool(opmix),
            "note": "" if opmix else "AVR CPU does not tag OpClass (committedInstType all 0; "
                                     "load/store/mem counters 0) — needs gem5 instrumentation (F2).",
            "classes": opmix,
        },
        "raw": {"stats": f"{run_id}.stats.txt", "trace_cmp": a.trace_cmp},
        "notes": a.notes,
    }

    outdir = os.path.join(a.results, a.category, a.workload)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, run_id + ".json"), "w") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")
    shutil.copyfile(a.stats, os.path.join(outdir, run_id + ".stats.txt"))
    print(f"recorded {run_id}  (match={match}, simInsts={metrics.get('simInsts')}, "
          f"cycles={metrics.get('numCycles')}, opmix={'yes' if opmix else 'no'})")
    print(f"  -> {os.path.join(a.category, a.workload, run_id + '.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
