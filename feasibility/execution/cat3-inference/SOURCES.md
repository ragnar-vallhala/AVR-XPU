# Cat 3 — Light inference: collected sources

Retrieved 2026-06-14 from **ARM-software/CMSIS-NN @ main** (`Source/…`). License: **Apache-2.0**.
Maps to the Cat-3 kernels in [`../test-plan.md`](../test-plan.md).

| Plan | Kernel | File (`sources/cmsis-nn/…`) | Upstream path |
|---|---|---|---|
| 3.1 | Conv2D int8 | `arm_convolve_s8.c` | `ConvolutionFunctions/` |
| 3.1 | Depthwise conv int8 | `arm_depthwise_conv_s8.c` | `ConvolutionFunctions/` |
| 3.2 | Fully-connected / GEMM int8 | `arm_fully_connected_s8.c` | `FullyConnectedFunctions/` |
| 3.3 | Max pooling int8 | `arm_max_pool_s8.c` | `PoolingFunctions/` |
| 3.1/3.2 | **Inner MAC loops** (conv & FC delegate here) | `arm_nn_mat_mult_nt_t_s8.c`, `arm_nn_vec_mat_mult_t_s8.c` | `NNSupportFunctions/` |
| 3.4 | Tiny detector block | — composed from 3.1 + 3.2 (no separate file) | — |

Notes:
- Same scalar-vs-SIMD guard situation as Cat 2: characterize/compile the **scalar reference path**.
- The dominant primitive here is the **int8 sum-of-dot-product (MAC) with requantize** — directly
  comparable to XpulpNN's packed-SIMD MAC (the §4 ISA reference).
- `arm_fully_connected_s8.c` mostly delegates to `arm_nn_vec_mat_mult_t_s8`; pull that helper too
  if the op-count needs the inner loop (note for Level-A/B, not fetched yet).
