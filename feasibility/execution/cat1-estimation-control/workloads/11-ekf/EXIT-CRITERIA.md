# 1.1 EKF covariance predict — exit criteria

- **Source:** `../../sources/ekf-px4/px4-ecl-covariance.cpp` → `Ekf::predictCovariance()`
- **Common contract:** [`../EXIT-CONTRACT.md`](../EXIT-CONTRACT.md)

## Kernel under test
One `P' = F·P·Fᵀ + Q` step over the 24-state covariance. The microkernel extracts the body of
`predictCovariance()` (the `PS0…PS222` temporaries + `nextP(i,j)` assignments) into a standalone
function over a plain `float P[24][24]` with fixed quaternion / IMU-delta inputs — PX4 class,
`Vector24f`/`SquareMatrix24f`, and the kahan/symmetry helpers replaced by plain arrays/loops.

## Input (fixed, deterministic)
- `P0` — a fixed symmetric positive-definite 24×24 `float` covariance (documented seed in `harness/`).
- `q = [q0..q3]`, `delta_ang[3]`, `delta_vel[3]`, biases `[6]`, `dt = FILTER_UPDATE_PERIOD_S` — all literals.

## Exit scenario
`init(P0,q,imu) → for k in 1..N { nextP = predict(P); P = nextP } → validate(P) → exit(0|1)`.
Two-run difference: **N1 = 1**, **N2 = 11** (10-invocation isolation).

## Golden reference
`P` after the same `N` predicts, produced by the host-native build of the identical microkernel
(x86 fp32), stored as `harness/golden_P.h` (upper triangle, 300 elements).

## Trace checkpoints (Level D1 — this kernel does NOT fit the 328P)

Working set ~4.6 KB > 2 KB SRAM ⇒ **no Nano run**; validated by **Tier 1 only** (host reference +
matched intermediate traces). Emit as raw IEEE-754 hex, guarded by `#ifdef TRACE` (read-only snapshots):
- a fixed subset of `PS*` intermediates (e.g. `PS33, PS100, PS137, PS157, PS186, PS213, PS222`) — catches
  divergence *inside* the temporary-expression DAG, not just at the end;
- the full diagonal `nextP(i,i)` (24 values) after the predict;
- a CRC32 over the entire upper triangle (300 floats) — the final deterministic end-goal signature.

This kernel is pure `+ − × ÷` on fp32 (no transcendentals) ⇒ host and gem5 must match **bit-for-bit**
at every checkpoint. First mismatch localizes the offending AVR op.

## Workload-specific valid-exit additions
- **Tolerance:** bit-exact (32-bit hex) at every checkpoint; the `1e-4` relative bound is only a
  fallback if a non-mandated op sneaks in.
- **Validated output:** every trace checkpoint above + the final CRC32 signature.

## Hypothesis to confirm (what it should "use most")
fp32 MAC realised as **softfloat calls** (`__mulsf3`/`__addsf3`) on 8-bit AVR ⇒ expect a
call/`load`/`store`-heavy profile; working set ≈ 4.6 KB > 2 KB SRAM ⇒ heavy data-memory traffic.
