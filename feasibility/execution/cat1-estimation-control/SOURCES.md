# Cat 1 — Estimation & Control: collected sources

Retrieved 2026-06-14. Maps to the Cat-1 kernels in [`../test-plan.md`](../test-plan.md).
Verbatim upstream copies, kept for static op-count (Level A) and avr-gcc builds (Level B).

| Plan | Kernel | Files (`sources/…`) | Upstream | License |
|---|---|---|---|---|
| 1.1 | EKF covariance predict/update (24-state) | `ekf-px4/px4-ecl-covariance.cpp` | PX4-ECL `EKF/covariance.cpp` (also in study-material) | BSD-3-Clause |
| 1.2 | Madgwick AHRS (modern "Fusion") | `ahrs-fusion/FusionAhrs.{c,h}`, `FusionMath.h` | xioTechnologies/Fusion @ main | MIT |
| 1.2 | Madgwick AHRS (classic) | `ahrs-madgwick/MadgwickAHRS.{cpp,h}` | arduino-libraries/MadgwickAHRS @ master | ⚠ Madgwick-derived (verify; commonly GPL/PD) |
| 1.2 | Mahony AHRS | `ahrs-mahony/MahonyAHRS.{cpp,h}` | PaulStoffregen/MahonyAHRS @ master | ⚠ Madgwick-derived (verify) |
| 1.3 | Quaternion / rotation kernels | `quaternion-px4-matrix/Quaternion.hpp`, `Dcm.hpp` | PX4/PX4-Matrix @ master | BSD-3-Clause |
| 1.4 | PID + rate control | `pid-px4/PID.{cpp,hpp}`, `ratecontrol-px4/rate_control.{cpp,hpp}` | PX4-Autopilot `src/lib/{pid,rate_control}` @ main | BSD-3-Clause |
| 1.4 | Attitude control (P/quat) | `attitude-px4/AttitudeControl.{cpp,hpp}` | PX4-Autopilot `src/modules/mc_att_control/AttitudeControl` @ main | BSD-3-Clause |
| 1.5 | Control allocation / mixer | `allocation-px4/ControlAllocator.{cpp,hpp}` | PX4-Autopilot `src/modules/control_allocator` @ main | BSD-3-Clause |
| 1.6 | Biquad gyro filter (bridge) | — uses Cat-2 `arm_biquad_cascade_df1_f32.c` | — | — |

Notes:
- 1.2: three AHRS variants collected so we can pick the cleanest for the AVR build (the classic
  Madgwick/Mahony `.cpp` are small & self-contained → easiest to cross-compile; Fusion is the
  better-engineered reference for op structure).
- 1.3/1.4: PX4 `matrix`/control classes are header-heavy C++ templates; fine for op-counting, but
  Level-B builds will need a trimmed self-contained microkernel.
- 1.5: current PX4 `ControlAllocator.cpp` is the orchestrator; the numeric core is a pseudo-inverse
  matrix-vector multiply (overlaps Cat-2 `arm_mat_mult`).
