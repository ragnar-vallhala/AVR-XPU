#!/usr/bin/env python3
"""record_run.py — write a structured run-log record (schema avrxpu-run/1).

For each run it:
  - builds a run_id = <catShort>-<workload>-<elfsha8>-<unixtime>,
  - writes <run_id>.json / .stats.txt / .opmix.txt / .svg (all prefixed with the id),
  - archives the ELF under results/.../elf/<sha>.elf — ONLY for runs that worked
    (clean exit AND trace match); failing runs keep the record, not the ELF,
  - appends one row to the master index results/runs.csv.
See results/README.md.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time

METRIC_KEYS = {
    "simInsts": "simInsts",
    "simOps": "simOps",
    "system.cpu.numCycles": "numCycles",
    "system.cpu.cpi": "cpi",
    "system.cpu.ipc": "ipc",
    "system.cpu.commitStats0.numIntInsts": "numIntInsts",
}

CSV_FIELDS = ["run_id", "created_utc", "category", "workload", "kind", "iters", "valid",
              "simInsts", "numCycles", "cpi", "elf_archived", "elf_sha256",
              "record_json", "stats_file", "opmix_file", "svg_file", "note"]


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
    histo = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                histo[parts[0]] = int(parts[1])
    return dict(sorted(histo.items(), key=lambda kv: -kv[1]))


def sha256(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_svg(histo, title, total, top=20):
    items = list(histo.items())[:top]
    if not items:
        return None
    total = total or sum(c for _, c in items)
    maxc = max(c for _, c in items)
    shown = sum(c for _, c in items)
    rowh, padt, padl, barmax = 20, 58, 96, 500
    w, h = padl + barmax + 180, padt + rowh * len(items) + 14
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="monospace" font-size="12">',
         f'<rect width="{w}" height="{h}" fill="white"/>',
         f'<text x="10" y="22" font-size="15" font-weight="bold">{title}</text>',
         f'<text x="10" y="42" font-size="11" fill="#555">total {total} insts across '
         f'{len(histo)} mnemonics; top {len(items)} = {100.0*shown/total:.1f}% of all</text>']
    for i, (mn, c) in enumerate(items):
        y = padt + i * rowh
        bw = max(1, round(barmax * c / maxc))
        o.append(f'<text x="{padl-6}" y="{y+13}" text-anchor="end">{mn}</text>')
        o.append(f'<rect x="{padl}" y="{y+3}" width="{bw}" height="{rowh-7}" fill="#4677c8"/>')
        o.append(f'<text x="{padl+bw+5}" y="{y+13}">{c}  {100.0*c/total:.1f}%</text>')
    o.append("</svg>")
    return "\n".join(o)


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
    p.add_argument("--note", default="", help="short free-text note (<100 chars)")
    p.add_argument("--results", required=True)
    p.add_argument("--no-store-elf", action="store_true")
    p.add_argument("--now", default="")
    p.add_argument("--unixtime", type=int, default=0)
    a = p.parse_args(argv)

    metrics = parse_stats(a.stats)
    opmix_path = a.opmix or os.path.join(os.path.dirname(a.stats) or ".", "avr_opmix.txt")
    histo = parse_opmix(opmix_path) if os.path.exists(opmix_path) else {}

    now = a.now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    unixt = a.unixtime or int(time.time())
    elf_sha = sha256(a.elf)
    cat_short = a.category.split("-")[0]                       # cat1-estimation-control -> cat1
    run_id = f"{cat_short}-{a.workload}-i{a.iters}-{(elf_sha or 'noelf')[:8]}-{unixt}"

    match = bool(a.host_crc) and a.host_crc == a.gem5_crc
    exit_ok = a.exit_cause == "AVR Syscall Exit"
    valid = exit_ok and match
    note = a.note[:99]

    outdir = os.path.join(a.results, a.category, a.workload)
    os.makedirs(outdir, exist_ok=True)

    # Per-run artifacts, all prefixed with run_id.
    stats_file = run_id + ".stats.txt"
    opmix_file = (run_id + ".opmix.txt") if histo else None
    svg_file = (run_id + ".svg") if histo else None
    shutil.copyfile(a.stats, os.path.join(outdir, stats_file))
    if histo:
        shutil.copyfile(opmix_path, os.path.join(outdir, opmix_file))
        svg = make_svg(histo, f"{a.workload} op-mix (top 20) — {run_id}",
                       total=sum(histo.values()))
        with open(os.path.join(outdir, svg_file), "w") as f:
            f.write(svg + "\n")

    # Archive the ELF ONLY for runs that worked (content-addressed by sha).
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
        "unixtime": unixt,
        "platform": {"runner": a.runner, "gem5_git": a.gem5_sha, "gem5_dirty": a.gem5_dirty},
        "build": {"mcu": a.mcu, "toolchain": a.toolchain, "cflags": a.cflags,
                  "iters": a.iters, "trace": a.trace,
                  "elf": os.path.basename(a.elf), "elf_sha256": elf_sha,
                  "elf_archived": elf_archived},
        "validation": {"host_crc": a.host_crc, "gem5_crc": a.gem5_crc,
                       "checkpoints": a.checkpoints, "match": match},
        "exit": {"cause": a.exit_cause, "ok": exit_ok},
        "metrics": metrics,
        "opmix": {"available": bool(histo), "total": sum(histo.values()) if histo else 0,
                  "classes": histo},
        "raw": {"stats": stats_file, "opmix": opmix_file, "svg": svg_file,
                "trace_cmp": a.trace_cmp},
        "note": note,
    }
    record_json = run_id + ".json"
    with open(os.path.join(outdir, record_json), "w") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")

    # Append to the master index.
    csv_path = os.path.join(a.results, "runs.csv")
    new = not os.path.exists(csv_path)
    rel = os.path.join(a.category, a.workload)
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "run_id": run_id, "created_utc": now, "category": a.category,
            "workload": a.workload, "kind": a.kind, "iters": a.iters, "valid": valid,
            "simInsts": metrics.get("simInsts"), "numCycles": metrics.get("numCycles"),
            "cpi": metrics.get("cpi"), "elf_archived": elf_archived, "elf_sha256": elf_sha,
            "record_json": os.path.join(rel, record_json),
            "stats_file": os.path.join(rel, stats_file),
            "opmix_file": os.path.join(rel, opmix_file) if opmix_file else "",
            "svg_file": os.path.join(rel, svg_file) if svg_file else "",
            "note": note,
        })

    top = list(histo.items())[:3]
    print(f"recorded {run_id}  valid={valid}  simInsts={metrics.get('simInsts')}  "
          f"opmix={'yes' if histo else 'no'} top={top}  elf={'kept' if elf_archived else 'no'}  "
          f"svg={'yes' if svg_file else 'no'}  -> runs.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
