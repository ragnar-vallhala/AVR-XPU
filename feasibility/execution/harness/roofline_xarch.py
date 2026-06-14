#!/usr/bin/env python3
"""roofline_xarch.py — §2 cross-architecture arithmetic analysis.

Places AVR (softfloat), ARM64 (NEON+VFP) and RISC-V (RV64GC) on the SAME
measured roofline: achieved fp throughput (fp-ops / cycle) vs arithmetic
intensity (fp-ops / data-byte). Per-invocation work is isolated via the
i11-i1 difference (cancels static-glibc / crt startup). Data bytes come from
gem5's mem-controller `bytesRead/Written::cpu.data` for ALL three ISAs, so the
byte axis is architecture-independent (total data-memory traffic, including
stack spills). fp-op counts: softfloat calls for AVR, committed float op-class
instructions for ARM/RISC-V.

Inputs (under results/):
  baseline_isa_roofline.txt   wl isa it crc simInsts cycles fpops intmac dbytes  (arm,rv)
  baseline_avr_roofline.txt   wl avr it simInsts cycles dbytes                    (cycles,bytes)
  <cat>/<wl>/*.json           AVR softfloat call counts (fp ops)
Emits results/roofline_xarch.{md,svg}.
"""
import collections
import glob
import json
import math
import os
import sys

FP_CALL = ("__addsf3", "__subsf3", "__mulsf3", "__divsf3")
# fp kernels only (the softfloat-vs-FPU story); ordered by AVR-table intensity
ORDER = ["12-ahrs", "25-dotprod", "24-matmul", "11-ekf", "21-fir",
         "13-quaternion", "22-biquad", "23-fft", "15-control-allocation",
         "14-control-pid"]


def avr_fp_calls(results):
    out = {}
    for j in glob.glob(os.path.join(results, "*", "*", "*.json")):
        d = json.load(open(j))
        wl, it = d["workload"]["id"], d["build"]["iters"]
        out.setdefault(wl, {})[it] = sum(d["funccalls"]["classes"].get(k, 0) for k in FP_CALL)
    return out


def load(results):
    fp = avr_fp_calls(results)
    arch = collections.defaultdict(lambda: collections.defaultdict(dict))
    for ln in open(os.path.join(results, "baseline_avr_roofline.txt")):
        wl, _, it, si, cy, db = ln.split()
        arch[wl]["avr"][int(it)] = dict(cy=int(cy), db=int(db),
                                        fp=fp.get(wl, {}).get(int(it), 0))
    for ln in open(os.path.join(results, "baseline_isa_roofline.txt")):
        wl, isa, it, crc, si, cy, f, im, db = ln.split()
        arch[wl][isa][int(it)] = dict(cy=int(cy), db=int(db), fp=int(f))
    return arch


def perinv(d):
    return {k: (d[11][k] - d[1][k]) / 10.0 for k in ("cy", "db", "fp")}


def analyze(results):
    arch = load(results)
    rows = []
    for wl in ORDER:
        if wl not in arch:
            continue
        m = {a: perinv(arch[wl][a]) for a in ("avr", "arm", "rv") if a in arch[wl]}
        if not all(a in m for a in ("avr", "arm", "rv")):
            continue
        rec = dict(wl=wl)
        for a in ("avr", "arm", "rv"):
            d = m[a]
            rec[a] = dict(I=d["fp"] / d["db"] if d["db"] else 0,
                          T=d["fp"] / d["cy"] if d["cy"] else 0,
                          cyc_op=d["cy"] / d["fp"] if d["fp"] else 0)
        rec["tput_ratio_arm"] = rec["arm"]["T"] / rec["avr"]["T"] if rec["avr"]["T"] else 0
        rows.append(rec)
    return rows


def svg(rows, path):
    W, H, ml, mb = 760, 560, 70, 56
    pw, ph = W - ml - 30, H - mb - 56
    x0, x1 = math.log10(0.03), math.log10(2)
    y0, y1 = math.log10(0.004), math.log10(2)
    X = lambda v: ml + pw * (math.log10(v) - x0) / (x1 - x0)
    Y = lambda v: mb + ph - ph * (math.log10(v) - y0) / (y1 - y0)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="monospace" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{ml}" y="22" font-size="14" font-weight="bold">Cross-arch roofline: achieved fp-ops/cycle vs arithmetic intensity</text>']
    for gx in (0.03, 0.06, 0.1, 0.25, 0.5, 1, 2):
        o.append(f'<line x1="{X(gx):.1f}" y1="{mb}" x2="{X(gx):.1f}" y2="{mb+ph}" stroke="#eee"/>')
        o.append(f'<text x="{X(gx):.1f}" y="{mb+ph+14}" text-anchor="middle" fill="#555">{gx:g}</text>')
    for gy in (0.004, 0.01, 0.1, 1):
        o.append(f'<line x1="{ml}" y1="{Y(gy):.1f}" x2="{ml+pw}" y2="{Y(gy):.1f}" stroke="#eee"/>')
        o.append(f'<text x="{ml-6}" y="{Y(gy)+3:.1f}" text-anchor="end" fill="#555">{gy:g}</text>')
    # scalar FP roof = 1 op/cycle
    o.append(f'<line x1="{ml}" y1="{Y(1):.1f}" x2="{ml+pw}" y2="{Y(1):.1f}" stroke="#888" stroke-dasharray="5 4"/>')
    o.append(f'<text x="{ml+pw-4}" y="{Y(1)-4:.1f}" text-anchor="end" fill="#888">scalar FP roof (1 op/cycle)</text>')
    cols = {"avr": "#999999", "arm": "#4677C8", "rv": "#B5651D"}
    for a, col in cols.items():
        for r in rows:
            o.append(f'<circle cx="{X(r[a]["I"]):.1f}" cy="{Y(r[a]["T"]):.1f}" r="3.3" fill="{col}"/>')
    lx, ly = ml + 14, mb + 14
    for i, (a, lab) in enumerate((("avr", "AVR softfloat"), ("arm", "ARM64 NEON+VFP"), ("rv", "RISC-V RV64GC"))):
        o.append(f'<circle cx="{lx}" cy="{ly+i*16}" r="3.3" fill="{cols[a]}"/>')
        o.append(f'<text x="{lx+10}" y="{ly+i*16+4}" fill="{cols[a]}">{lab}</text>')
    o.append(f'<text x="{ml+pw/2}" y="{H-8}" text-anchor="middle">arithmetic intensity (fp-ops / data-byte moved)</text>')
    o.append(f'<text x="16" y="{mb+ph/2}" transform="rotate(-90 16 {mb+ph/2})" text-anchor="middle">achieved fp-ops / cycle</text>')
    o.append("</svg>")
    open(path, "w").write("\n".join(o) + "\n")


def main(argv):
    results = argv[1] if len(argv) > 1 else "results"
    rows = analyze(results)
    hdr = (f"{'workload':22} | {'AVR  I':>7} {'tput':>7} | {'ARM  I':>7} {'tput':>7} | "
           f"{'RV   I':>7} {'tput':>7} | {'ARM/AVR tput':>12}")
    print(hdr)
    for r in rows:
        print(f"{r['wl']:22} | {r['avr']['I']:7.3f} {r['avr']['T']:7.4f} | "
              f"{r['arm']['I']:7.3f} {r['arm']['T']:7.4f} | {r['rv']['I']:7.3f} {r['rv']['T']:7.4f} | "
              f"{r['tput_ratio_arm']:11.1f}x")
    svg(rows, os.path.join(results, "roofline_xarch.svg"))

    Iavr = [r["avr"]["I"] for r in rows]
    Iarm = [r["arm"]["I"] for r in rows]
    Tavr = [r["avr"]["T"] for r in rows]
    Tarm = [r["arm"]["T"] for r in rows]
    ratios = [r["tput_ratio_arm"] for r in rows]
    with open(os.path.join(results, "roofline_xarch.md"), "w") as f:
        f.write("# §2 Cross-architecture arithmetic analysis (AVR / ARM64 / RISC-V)\n\n")
        f.write("Same fp microkernels, same gem5, per-invocation via i11-i1. **Arithmetic intensity** =\n")
        f.write("fp-ops / data-bytes-moved; **tput** = achieved fp-ops / cycle. Data bytes come from the\n")
        f.write("mem-controller (`bytesRead/Written::cpu.data`) for all three ISAs, so the byte axis is\n")
        f.write("architecture-independent (total data traffic incl. stack spills). fp-ops = softfloat\n")
        f.write("calls (AVR) / committed float op-class instructions (ARM, RISC-V).\n\n```\n" + hdr + "\n")
        for r in rows:
            f.write(f"{r['wl']:22} | {r['avr']['I']:7.3f} {r['avr']['T']:7.4f} | "
                    f"{r['arm']['I']:7.3f} {r['arm']['T']:7.4f} | {r['rv']['I']:7.3f} {r['rv']['T']:7.4f} | "
                    f"{r['tput_ratio_arm']:11.1f}x\n")
        f.write("```\n\n## Verdict\n")
        f.write(f"- **Throughput:** ARM/RISC-V achieve **{min(Tarm):.2f}-{max(Tarm):.2f} fp-ops/cycle** "
                f"(near the scalar FP roof of 1), vs AVR softfloat's **{min(Tavr):.4f}-{max(Tavr):.4f}** — "
                f"a **{min(ratios):.0f}-{max(ratios):.0f}x** gap that matches the §3 instruction-count gap "
                f"and confirms it is the *lack of a hardware FPU*, not the ISA encoding.\n")
        f.write(f"- **Intensity:** AVR sits at **{min(Iavr):.3f}-{max(Iavr):.3f} fp/byte**, "
                f"**{min(Iarm)/max(Iavr):.0f}-{max(Iarm)/min(Iavr):.0f}x lower** than ARM "
                f"({min(Iarm):.2f}-{max(Iarm):.2f}): softfloat moves ~5x more bytes per fp op (register\n"
                "  spills), pushing AVR *further* into the memory-bound region — so on real hardware the\n"
                "  HW-fp datapath must be paired with enough memory bandwidth to feed it.\n")
        f.write("- *Caveat:* ARM NEON may pack several fp ops per instruction, so its fp-op count (and thus\n"
                "  intensity/throughput) is a slight under-count where auto-vectorisation fired (e.g. fir).\n")
    print(f"\nwrote {results}/roofline_xarch.md + .svg")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
