# Cat 2 — DSP / mid-tier: collected sources

Retrieved 2026-06-14 from **ARM-software/CMSIS-DSP @ main** (`Source/…`). License: **Apache-2.0**.
Maps to the Cat-2 kernels in [`../test-plan.md`](../test-plan.md).

| Plan | Kernel | File (`sources/cmsis-dsp/…`) | Upstream path |
|---|---|---|---|
| 2.1 | FIR filter (fp32) | `arm_fir_f32.c` | `FilteringFunctions/` |
| 2.2 | Biquad IIR cascade DF1 (fp32) | `arm_biquad_cascade_df1_f32.c` | `FilteringFunctions/` |
| 2.3 | Real FFT (fp32) | `arm_rfft_fast_f32.c` | `TransformFunctions/` |
| 2.4 | Matrix multiply (fp32) | `arm_mat_mult_f32.c` | `MatrixFunctions/` |
| 2.4 | Cholesky decomposition (fp32) | `arm_mat_cholesky_f32.c` | `MatrixFunctions/` |
| 2.4 | Matrix inverse (fp32) | `arm_mat_inverse_f32.c` | `MatrixFunctions/` |
| 2.5 | Vector dot product (fp32) | `arm_dot_prod_f32.c` | `BasicMathFunctions/` |

Notes:
- Each file contains Helium (MVE) / Neon **and** scalar paths under `#if defined(...)` guards.
  For AVR we characterize/compile the **scalar reference path** (none of `ARM_MATH_MVEF`/`NEON`
  defined) — that is exactly the softfloat baseline we want.
- For reproducibility of the final artifact, pin to a CMSIS-DSP release tag/commit (currently `main`).
