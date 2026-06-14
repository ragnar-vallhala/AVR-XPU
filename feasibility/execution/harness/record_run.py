#!/usr/bin/env python3
"""record_run.py — write a structured run-log record (schema avrxpu-run/1).

Ingests a gem5 stats.txt plus the three AVR-CPU histograms emitted at exit:
  avr_opmix.txt         per-mnemonic instruction count (op-mix)
  avr_opmix_cycles.txt  per-mnemonic cycle count       (where cycles go)
  avr_funcmix.txt       per-function instruction count (PC symbol)
Derives memory traffic + arithmetic intensity from the op-mix, writes one JSON
record + retains the raw histograms + an SVG per histogram (all prefixed with
the run_id), archives the ELF (valid runs only), and appends a row to runs.csv.

run_id = <catShort>-<workload>-i<iters>-<elfsha8>-<unixtime>. See results/README.md.
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
    "simInsts": "simInsts", "simOps": "simOps",
    "system.cpu.numCycles": "numCycles", "system.cpu.cpi": "cpi", "system.cpu.ipc": "ipc",
}
CSV_FIELDS = ["run_id", "created_utc", "category", "workload", "kind", "iters", "valid",
              "simInsts", "numCycles", "cpi", "arith_ipb", "elf_archived", "elf_sha256",
              "record_json", "stats_file", "opmix_file", "opmix_svg",
              "cycles_file", "funcmix_file", "note"]

# AVR mnemonics that move a byte to/from memory (data, stack, or program memory).
# Excludes ldi (load-immediate), mov/movw (reg-reg) and in/out (peripheral I/O).
def is_mem(mn):
    return mn in ("push", "pop", "lds", "sts") or \
        mn.startswith(("ld_", "st_", "ldd", "std", "lpm", "elpm"))


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


def parse_hist(path):
    h = {}
    if not path or not os.path.exists(path):
        return h
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split()
            if len(p) == 2 and p[1].isdigit():
                h[p[0]] = int(p[1])
    return dict(sorted(h.items(), key=lambda kv: -kv[1]))


def sha256(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def make_svg(histo, title, total, top=20):
    items = list(histo.items())[:top]
    if not items:
        return None
    total = total or sum(c for _, c in items)
    maxc = max(c for _, c in items)
    shown = sum(c for _, c in items)
    padl = max(96, 12 + 7 * max(len(mn) for mn, _ in items))
    rowh, padt, barmax = 20, 58, 470
    w, h = padl + barmax + 170, padt + rowh * len(items) + 14
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="monospace" font-size="12">',
         f'<rect width="{w}" height="{h}" fill="white"/>',
         f'<text x="10" y="22" font-size="15" font-weight="bold">{title}</text>',
         f'<text x="10" y="42" font-size="11" fill="#555">total {total} across {len(histo)} '
         f'entries; top {len(items)} = {100.0*shown/total:.1f}%</text>']
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
    p.add_argument("--m5out", default="", help="gem5 outdir (default: dir of --stats)")
    p.add_argument("--elf", default="")
    p.add_argument("--iters", type=int, default=1)
    p.add_argument("--trace", action="store_true")
    p.add_argument("--mcu", default="")
    p.add_argument("--cflags", default="-O1 -ffp-contract=off -fno-fast-math")
    p.add_argument("--toolchain", default="avr-gcc 7.3.0")
    p.add_argument("--gem5-sha", default="")
    p.add_argument("--runner", default="navrobotec")
    p.add_argument("--host-crc", default="")
    p.add_argument("--gem5-crc", default="")
    p.add_argument("--checkpoints", type=int, default=0)
    p.add_argument("--exit-cause", default="")
    p.add_argument("--trace-cmp", default="")
    p.add_argument("--note", default="")
    p.add_argument("--results", required=True)
    p.add_argument("--no-store-elf", action="store_true")
    p.add_argument("--now", default="")
    p.add_argument("--unixtime", type=int, default=0)
    a = p.parse_args(argv)

    m5 = a.m5out or (os.path.dirname(a.stats) or ".")
    metrics = parse_stats(a.stats)
    opmix = parse_hist(os.path.join(m5, "avr_opmix.txt"))
    cycmix = parse_hist(os.path.join(m5, "avr_opmix_cycles.txt"))
    funcmix = parse_hist(os.path.join(m5, "avr_funcmix.txt"))

    # #1 arithmetic intensity: memory traffic derived from the op-mix.
    total_i = sum(opmix.values()) if opmix else (metrics.get("simInsts") or 0)
    mem_i = sum(c for mn, c in opmix.items() if is_mem(mn))
    comp_i = total_i - mem_i
    ipb = round(comp_i / mem_i, 3) if mem_i else None  # compute insts per byte moved
    metrics["mem_insts"] = mem_i
    metrics["bytes_moved"] = mem_i           # AVR ld/st move 1 byte each
    metrics["compute_insts"] = comp_i
    metrics["insts_per_byte"] = ipb

    now = a.now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    unixt = a.unixtime or int(time.time())
    elf_sha = sha256(a.elf)
    run_id = f"{a.category.split('-')[0]}-{a.workload}-i{a.iters}-{(elf_sha or 'noelf')[:8]}-{unixt}"
    match = bool(a.host_crc) and a.host_crc == a.gem5_crc
    exit_ok = a.exit_cause == "AVR Syscall Exit"
    valid = exit_ok and match
    note = a.note[:99]

    outdir = os.path.join(a.results, a.category, a.workload)
    os.makedirs(outdir, exist_ok=True)

    def save(histo, src_name, suffix, title):
        if not histo:
            return (None, None)
        txt = run_id + suffix + ".txt"
        if os.path.exists(os.path.join(m5, src_name)):
            shutil.copyfile(os.path.join(m5, src_name), os.path.join(outdir, txt))
        svg_name = run_id + suffix + ".svg"
        with open(os.path.join(outdir, svg_name), "w") as f:
            f.write(make_svg(histo, f"{a.workload} {title} — {run_id}", sum(histo.values())) + "\n")
        return (txt, svg_name)

    stats_file = run_id + ".stats.txt"
    shutil.copyfile(a.stats, os.path.join(outdir, stats_file))
    opmix_txt, opmix_svg = save(opmix, "avr_opmix.txt", ".opmix", "op-mix (insts)")
    cyc_txt, cyc_svg = save(cycmix, "avr_opmix_cycles.txt", ".cycles", "op-mix (cycles)")
    func_txt, func_svg = save(funcmix, "avr_funcmix.txt", ".funcmix", "function-mix")

    elf_archived = None
    if valid and a.elf and elf_sha and not a.no_store_elf:
        elfdir = os.path.join(outdir, "elf")
        os.makedirs(elfdir, exist_ok=True)
        dest = os.path.join(elfdir, elf_sha[:12] + ".elf")
        if not os.path.exists(dest):
            shutil.copyfile(a.elf, dest)
        elf_archived = os.path.relpath(dest, a.results)

    def section(h):
        return {"available": bool(h), "total": sum(h.values()) if h else 0, "classes": h}

    rec = {
        "schema": "avrxpu-run/1", "run_id": run_id,
        "workload": {"id": a.workload, "category": a.category, "kernel": a.kernel},
        "kind": a.kind, "created_utc": now, "unixtime": unixt,
        "platform": {"runner": a.runner, "gem5_git": a.gem5_sha},
        "build": {"mcu": a.mcu, "toolchain": a.toolchain, "cflags": a.cflags,
                  "iters": a.iters, "trace": a.trace, "elf": os.path.basename(a.elf),
                  "elf_sha256": elf_sha, "elf_archived": elf_archived},
        "validation": {"host_crc": a.host_crc, "gem5_crc": a.gem5_crc,
                       "checkpoints": a.checkpoints, "match": match},
        "exit": {"cause": a.exit_cause, "ok": exit_ok},
        "metrics": metrics,
        "opmix": section(opmix), "opmix_cycles": section(cycmix), "funcmix": section(funcmix),
        "raw": {"stats": stats_file, "opmix": opmix_txt, "opmix_svg": opmix_svg,
                "cycles": cyc_txt, "cycles_svg": cyc_svg, "funcmix": func_txt,
                "funcmix_svg": func_svg, "trace_cmp": a.trace_cmp},
        "note": note,
    }
    record_json = run_id + ".json"
    with open(os.path.join(outdir, record_json), "w") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")

    rel = os.path.join(a.category, a.workload)
    j = lambda x: os.path.join(rel, x) if x else ""
    csv_path = os.path.join(a.results, "runs.csv")
    new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"run_id": run_id, "created_utc": now, "category": a.category,
                    "workload": a.workload, "kind": a.kind, "iters": a.iters, "valid": valid,
                    "simInsts": metrics.get("simInsts"), "numCycles": metrics.get("numCycles"),
                    "cpi": metrics.get("cpi"), "arith_ipb": ipb, "elf_archived": elf_archived,
                    "elf_sha256": elf_sha, "record_json": j(record_json), "stats_file": j(stats_file),
                    "opmix_file": j(opmix_txt), "opmix_svg": j(opmix_svg), "cycles_file": j(cyc_txt),
                    "funcmix_file": j(func_txt), "note": note})

    print(f"recorded {run_id}  valid={valid}  simInsts={metrics.get('simInsts')}  "
          f"mem={mem_i} ipb={ipb}  opmix/cyc/func={'Y' if opmix else 'N'}"
          f"{'Y' if cycmix else 'N'}{'Y' if funcmix else 'N'}  elf={'kept' if elf_archived else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
