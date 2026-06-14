/* dotprod_kernel.c — fp32 vector dot product (CMSIS arm_dot_prod_f32 scalar form).
 * s = sum_i A[i]*B[i]. Pure MAC. */
#include <stdint.h>
#include "harness.h"

#define N 64
static float A[N], B[N];

uint32_t run_workload(int iters) {
  for (int i = 0; i < N; i++) {
    A[i] = 0.01f * (float)(i + 1);
    B[i] = 0.5f * (float)((i % 7) - 3);
  }
  float acc = 0.0f;
  for (int k = 0; k < iters; k++) {
    float s = 0.0f;
    for (int i = 0; i < N; i++)
      s += A[i] * B[i];
    acc += s;
    A[k % N] += 1e-4f * s; /* perturb so iterations differ (anti-DCE) */
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, &acc, 4);
  TRACE_F32("dot", acc);
  return crc;
}
