# 1.2 Attitude estimation (AHRS) — exit criteria

- **Sources:** `../../sources/ahrs-madgwick/MadgwickAHRS.cpp`, `../../sources/ahrs-mahony/MahonyAHRS.cpp`
  (classic, self-contained — preferred for the AVR build); `../../sources/ahrs-fusion/` as the reference structure.
- **Common contract:** [`../EXIT-CONTRACT.md`](../EXIT-CONTRACT.md)

## Kernel under test
One AHRS **update step** — the IMU (6-axis) or MARG (9-axis) update that takes gyro/accel(/mag) and
the current attitude quaternion to the next quaternion (gradient-descent for Madgwick; PI feedback +
integral for Mahony). Run both variants separately so the op-mix can be compared.

## Input (fixed, deterministic)
- A fixed short sample stream (e.g. 64 samples) of `gyro[3]`, `accel[3]`, `mag[3]` literals,
  plus a fixed sample period `dt`. Same stream for both variants.

## Exit scenario
`init(q=identity) → for s in stream (looped to N total steps) { q = update(q, gyro,accel,mag,dt) } → validate(q) → exit(0|1)`.
Two-run difference on total step count: **N1 = 64**, **N2 = 640**.

## Golden reference
Final quaternion `q` after `N` steps from the host-native build of the same update, per variant:
`harness/golden_q_madgwick.h`, `harness/golden_q_mahony.h`.

## Workload-specific valid-exit additions
- **Tolerance:** `|Δq_i| ≤ 1e-4` per component (softfloat; also accept the negated quaternion −q as equal).
- **Validated output:** the 4 quaternion components after `N` steps.

## Hypothesis to confirm
fp32 MAC + one **`invSqrt`/`sqrtf`** per step (normalization). Far smaller working set than EKF
(tens of floats) ⇒ likely **compute-bound on softfloat**, not memory-bound — a useful contrast to 1.1.
