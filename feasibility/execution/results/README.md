# Results / run-log model

Run logs are **data, not scratch** — every gem5/host run is recorded here, versioned in git, so results
are reproducible and aggregatable. Nothing under `results/` is throwaway.

## Layout

```
results/
  README.md                         # this spec
  <category>/<workload>/
    <run_id>.json                   # the structured record (schema avrxpu-run/1)
    <run_id>.stats.txt              # the raw gem5 stats.txt for that run (retained verbatim)
```

`run_id = <workload>_<UTC-timestamp>_<gem5sha8>_i<iters>` — unique per run, sortable, self-describing.

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
