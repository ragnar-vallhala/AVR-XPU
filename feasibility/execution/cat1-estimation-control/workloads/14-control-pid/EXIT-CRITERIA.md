# 1.4 Cascaded PID / rate control — exit criteria

- **Sources:** `../../sources/pid-px4/PID.cpp`, `../../sources/ratecontrol-px4/rate_control.cpp`,
  `../../sources/attitude-px4/AttitudeControl.cpp`
- **Common contract:** [`../EXIT-CONTRACT.md`](../EXIT-CONTRACT.md)

## Kernel under test
One **control step** of the inner loop: attitude (P on quaternion error) → rate PID
(P+I+D with feedforward and integral anti-windup) → torque setpoint. The rate-PID step is the hot
inner kernel; characterize it as the primary, with the attitude P-step as a secondary.
Microkernel: strip the PX4 classes to plain state structs + the update math; no uORB/params.

## Input (fixed, deterministic)
- Fixed setpoint (attitude/rate), fixed measured state, fixed gains, fixed `dt`.
- A fixed short sequence of setpoint/measurement pairs so the integral/derivative terms are exercised
  (not a constant input that zeroes I/D).

## Exit scenario
`init(state,gains) → for k in 1..N { torque = control_step(state, setpoint[k mod M], dt) } → validate(accumulated torque + integrator state) → exit(0|1)`.
Two-run difference: **N1 = 100**, **N2 = 1100**.

## Golden reference
Accumulated torque outputs + final integrator state after `N` steps from the host-native build:
`harness/golden_pid.h`.

## Workload-specific valid-exit additions
- **Tolerance:** `1e-4` relative. Integrator state must match (catches anti-windup / clamp divergence).
- **Validated output:** 3-axis torque accumulation + integrator state.

## Hypothesis to confirm
Mostly fp32 mul/add/compare (the saturate/clamp branches) with a **branch-heavier** profile than
1.1–1.3 (anti-windup, limits). Tiny working set ⇒ compute/branch-bound, not memory-bound.
