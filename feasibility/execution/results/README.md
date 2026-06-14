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
    <run_id>.opmix.txt              # raw per-mnemonic op-mix (avr_opmix.txt)
    <run_id>.svg                    # op-mix histogram (top 20)
    elf/<elfsha12>.elf              # the ELF — kept ONLY for runs that worked, content-addressed by sha
```

`run_id = <catShort>-<workload>-<elfsha8>-<unixtime>` (e.g. `cat1-11-ekf-501853ba-1781451428`) — every
per-run artifact is prefixed with it. **`runs.csv`** is the cross-run master index; columns: run_id,
created_utc, category, workload, kind, valid, simInsts, numCycles, cpi, elf_archived, elf_sha256,
record_json, stats_file, opmix_file, svg_file, note (<100 chars).

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
