# Results / run-log model

Run logs are **data, not scratch** — every gem5/host run is recorded here, versioned in git, so results
are reproducible and aggregatable. Nothing under `results/` is throwaway.

## Layout

```
results/
  README.md                         # this spec
  runs.csv                          # master index: one row per run (elf, result files, artifacts, note)
  <category>/<workload>/
    <run_id>.json                   # structured record (schema avrxpu-run/1)
    <run_id>.stats.txt              # raw gem5 stats.txt (retained verbatim)
    <run_id>.opmix.txt   .opmix.svg     # per-mnemonic INSTRUCTION op-mix + histogram
    <run_id>.cycles.txt  .cycles.svg    # per-mnemonic CYCLE op-mix (where cycles go) + histogram
    <run_id>.funcmix.txt .funcmix.svg   # per-FUNCTION instruction count (PC symbol; e.g. __divsf3)
    <run_id>.funccyc.txt .funccyc.svg   # per-FUNCTION CYCLE count (cycles spent per function)
    elf/<elfsha12>.elf              # the ELF — kept ONLY for runs that worked, content-addressed by sha
```

`run_id = <catShort>-<workload>-i<iters>-<elfsha8>-<unixtime>` (e.g. `cat1-11-ekf-i1-501853ba-1781451428`)
— every per-run artifact is prefixed with it. **`runs.csv`** is the cross-run master index; columns:
run_id, created_utc, category, workload, kind, iters, valid, simInsts, numCycles, cpi, **arith_ipb**
(compute insts per byte moved), elf_archived, elf_sha256, record_json, stats_file, opmix_file,
opmix_svg, cycles_file, funcmix_file, funccyc_file, note (<100 chars).

### Data axes per run
- **op-mix** (`opmix`) — what instructions run most.
- **cycle-weighted op-mix** (`opmix_cycles`) — where the *cycles* go (count × per-op cycle cost).
- **function-mix** — which functions/symbols dominate, by **instructions** (`funcmix`) and by
  **cycles** (`funcmix_cycles`); e.g. softfloat `__divsf3`. The cycle view re-ranks multi-cycle-heavy
  functions (e.g. `__fp_round`) above their instruction-count rank.
- **arithmetic intensity** (`metrics.mem_insts / bytes_moved / compute_insts / insts_per_byte`) —
  data-memory traffic derived from the op-mix; the roofline / memory-bound input.

## Record schema — `avrxpu-run/1`

```jsonc
{
  "schema": "avrxpu-run/1",
  "run_id": "...",
  "workload": { "id", "category", "kernel" },     // which kernel
  "kind": "measurement" | "validation" | "derived-per-invocation",
  "created_utc": "ISO-8601",
  "platform": { "runner", "gem5_git", "gem5_dirty" },
  "build":    { "mcu", "toolchain", "cflags", "iters", "trace", "elf", "elf_sha256" },
  "validation": { "host_crc", "gem5_crc", "checkpoints", "match" },  // host+trace oracle
  "exit":       { "cause", "ok" },                                   // AVR Syscall Exit = ok
  "metrics":  { "simInsts","simOps","numCycles","cpi","ipc",
                "numIntInsts","numLoadInsts","numStoreInsts","numMemRefs","numFpInsts" },
  "opmix":    { "available": bool, "note": "...", "classes": { <name>: count } },
  "raw":      { "stats", "trace_cmp" },
  "notes": "..."
}
```

## Conventions

- **Op-mix isolation = two-run difference.** Record both an `i<N1>` and an `i<N2>` run; a
  `derived-per-invocation` record references both and stores `(metric_N2 − metric_N1)/(N2 − N1)`.
- **Validation gates measurement.** Only `exit.ok && validation.match` runs are trusted; others are
  still recorded (with the failure) — a failed run is also data.
- **`opmix.available` is `false`** until the AVR CPU is instrumented to tag op classes / per-opcode
  counts (gem5 currently leaves `committedInstType::*` and the load/store/mem counters at 0). Tracked
  as finding **F2** (see `cat1-estimation-control/workloads/11-ekf/harness/FINDINGS.md`). The schema already
  reserves `opmix.classes` so records gain the histogram with no schema change once instrumented.

## Writer

`../harness/record_run.py` parses a gem5 `stats.txt` + run metadata and emits the JSON record + retains
the raw stats. See its `--help`.
