# 1.5 Control allocation / mixer — exit criteria

- **Source:** `../../sources/allocation-px4/ControlAllocator.cpp` (orchestrator); the numeric core is a
  pseudo-inverse matrix-vector multiply `u = B⁺ · [τ; T]`.
- **Common contract:** [`../EXIT-CONTRACT.md`](../EXIT-CONTRACT.md)

## Kernel under test
The **allocation step**: given a fixed actuator-effectiveness pseudo-inverse `B⁺` (n_actuators × 4)
and a control setpoint `[τx τy τz T]`, compute the actuator vector `u`, then apply per-actuator
clamp/saturation. Characterize the mat-vec + clamp; the off-line pseudo-inverse computation is
**out of scope** (done once at config time, not per control step).
Microkernel: a fixed `B⁺` (e.g. quad-X, 4 actuators) as a literal `float` matrix + the multiply + clamp.

## Input (fixed, deterministic)
- Fixed `B⁺` for a chosen airframe (quad-X default), fixed setpoint sequence (M setpoints) that drives
  some actuators into saturation so the clamp path is exercised.

## Exit scenario
`init(Bpinv) → for k in 1..N { u = allocate(Bpinv, setpoint[k mod M]); accumulate(u) } → validate(accumulated u) → exit(0|1)`.
Two-run difference: **N1 = 100**, **N2 = 1100**.

## Golden reference
Accumulated `u` after `N` allocations from the host-native build: `harness/golden_alloc.h`.

## Workload-specific valid-exit additions
- **Tolerance:** `1e-4` relative. Saturation behavior (clamped actuators) must match exactly in pattern.
- **Validated output:** the n-actuator vector accumulation.

## Hypothesis to confirm
Small dense fp32 **mat-vec MAC** + clamp branches — structurally the same MAC primitive as Cat-2
`arm_mat_mult`, at tiny size. Confirms whether allocation shares the EKF/DSP MAC path (it should),
i.e. one fused-MAC primitive serves 1.1, 1.5 and Cat-2.
