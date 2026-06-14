#!/usr/bin/env python3
"""compare_trace.py — validate a gem5 run against the host reference.

Both traces are line streams of "<id> <8-hex>" plus a final "CRC <hex>" and
"PASS"/"FAIL". Compares line-by-line, reports the FIRST divergence (that pins
the offending op/checkpoint), and checks the end-goal CRC matches.

Usage: compare_trace.py HOST_TRACE GEM5_TRACE
Exit 0 = identical (valid gem5 run); 1 = divergence; 2 = usage/IO error.
"""
import sys


def load(path):
    rows, crc = [], None
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("CRC "):
                crc = line.split()[1].lower()
            elif line in ("PASS", "FAIL"):
                pass
            else:
                parts = line.split()
                if len(parts) == 2:
                    rows.append((parts[0], parts[1].lower()))
    return rows, crc


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    href, hcrc = load(argv[1])
    gref, gcrc = load(argv[2])
    n = min(len(href), len(gref))
    for i in range(n):
        if href[i] != gref[i]:
            print(f"DIVERGENCE at checkpoint #{i}:")
            print(f"  host: {href[i][0]} {href[i][1]}")
            print(f"  gem5: {gref[i][0]} {gref[i][1]}")
            return 1
    if len(href) != len(gref):
        print(f"LENGTH MISMATCH: host {len(href)} vs gem5 {len(gref)} checkpoints "
              f"(first {n} agree) — likely a skipped/extra op in gem5.")
        return 1
    if hcrc != gcrc:
        print(f"CRC MISMATCH: host {hcrc} vs gem5 {gcrc}")
        return 1
    print(f"OK: {len(href)} checkpoints match; CRC {hcrc}. gem5 run is VALID.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
