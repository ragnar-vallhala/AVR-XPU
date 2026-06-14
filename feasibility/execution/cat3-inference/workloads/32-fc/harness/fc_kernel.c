/* fc_kernel.c — int8 fully-connected / GEMM (CMSIS-NN arm_fully_connected_s8 form).
 * out_s8[o] = requantize(bias[o] + sum_j W[o][j]*x[j]). Integer vec-mat MAC. */
#include <stdint.h>
#include "harness.h"

#define IN 32
#define OUT 16
static int8_t Wt[OUT][IN], x[IN];
static int32_t bias[OUT];
static int8_t out[OUT];

static int8_t requant(int32_t acc, int32_t mult, int shift) {
  int64_t v = (int64_t)acc * mult;
  int64_t r = (v + ((int64_t)1 << (shift - 1))) >> shift;
  if (r > 127) r = 127;
  else if (r < -128) r = -128;
  return (int8_t)r;
}

uint32_t run_workload(int iters) {
  for (int j = 0; j < IN; j++)
    x[j] = (int8_t)(((j * 13) % 255) - 127);
  for (int o = 0; o < OUT; o++) {
    bias[o] = (o - 8) * 2000;
    for (int j = 0; j < IN; j++)
      Wt[o][j] = (int8_t)(((o * 7 + j * 5) % 63) - 31);
  }
  const int32_t mult = 1073741824;
  const int shift = 41;

  for (int it = 0; it < iters; it++) {
    for (int o = 0; o < OUT; o++) {
      int32_t acc = bias[o];
      for (int j = 0; j < IN; j++)
        acc += (int32_t)Wt[o][j] * (int32_t)x[j];
      out[o] = requant(acc, mult, shift);
    }
    x[it % IN] += 1;
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, out, sizeof(out));
  TRACE_U32("fc", crc);
  return crc;
}
