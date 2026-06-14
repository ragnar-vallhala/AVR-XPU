# 1.3 Quaternion / rotation kernels — exit criteria

- **Source:** `../../sources/quaternion-px4-matrix/Quaternion.hpp`, `Dcm.hpp` (PX4 matrix lib)
- **Common contract:** [`../EXIT-CONTRACT.md`](../EXIT-CONTRACT.md)

## Kernels under test (the "glue" used by 1.1/1.2/1.4)
Run as separate micro-measurements so each op's cost is attributable:
- **q-mul** — Hamilton product of two quaternions.
- **normalize** — quaternion normalization (1 invSqrt).
- **rotate-vec** — rotate a 3-vector by a quaternion.
- **DCM build** — quaternion → 3×3 rotation matrix.
Microkernel: instantiate the PX4 templates at `float`, or transcribe the 4 ops into plain functions
(the templates are header-only and heavily inlined — transcription gives the cleanest AVR build).

## Input (fixed, deterministic)
- Two fixed unit quaternions `qa`, `qb` and a fixed 3-vector `v` (literals in `harness/`).

## Exit scenario
For each op: `for k in 1..N { out = op(inputs); feed out back to avoid dead-code elimination } → validate → exit(0|1)`.
Two-run difference per op: **N1 = 100**, **N2 = 1100**. Use `volatile`/accumulation so the compiler
cannot hoist or eliminate the loop body.

## Golden reference
Result of each op after `N` iterations from the host-native build: `harness/golden_quat.h`.

## Workload-specific valid-exit additions
- **Tolerance:** `1e-5` relative (short dependency chains, little accumulation error).
- **Anti-DCE requirement:** the validated value must depend on every loop iteration (accumulate),
  else the measurement is invalid even if it "exits cleanly".

## Hypothesis to confirm
Small fixed op-counts dominated by fp32 mul/add; **normalize/rotate add an invSqrt/div**. These set
the per-call softfloat cost that 1.1/1.2/1.4 inherit.
