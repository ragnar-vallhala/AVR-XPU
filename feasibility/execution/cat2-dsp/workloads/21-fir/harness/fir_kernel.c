/* fir_kernel.c — fp32 FIR filter (CMSIS arm_fir_f32 scalar form).
 * y[n] = sum_k b[k]*x[n-k] over a block; numTaps x blockSize MACs. */
#include <stdint.h>
#include "harness.h"

#define NTAPS 16
#define BLK 48
static float b[NTAPS], x[BLK], y[BLK];

uint32_t run_workload(int iters) {
  for (int k = 0; k < NTAPS; k++)
    b[k] = 0.05f * (float)((k % 5) + 1);
  for (int n = 0; n < BLK; n++)
    x[n] = 0.1f * (float)((n % 11) - 5);

  float acc = 0.0f;
  for (int it = 0; it < iters; it++) {
    for (int n = 0; n < BLK; n++) {
      float s = 0.0f;
      for (int k = 0; k < NTAPS; k++) {
        int idx = n - k;
        s += b[k] * (idx >= 0 ? x[idx] : 0.0f);
      }
      y[n] = s;
      acc += s;
    }
    x[it % BLK] += 1e-4f * acc; /* anti-DCE / vary iterations */
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, &acc, 4);
  TRACE_F32("fir", acc);
  return crc;
}
