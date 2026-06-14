/* conv2d_kernel.c — int8 quantized 2D convolution (CMSIS-NN arm_convolve_s8 form).
 * acc = bias + sum(in_s8 * w_s8); out_s8 = requantize(acc). Integer MAC +
 * int64 requantize — no softfloat (the int8-inference profile). */
#include <stdint.h>
#include "harness.h"

#define CIN 2
#define HH 8
#define WW 8
#define K 3
#define COUT 4
#define OH (HH - K + 1)
#define OW (WW - K + 1)
static int8_t in[CIN][HH][WW];
static int8_t wt[COUT][CIN][K][K];
static int32_t bias[COUT];
static int8_t out[COUT][OH][OW];

static int8_t requant(int32_t acc, int32_t mult, int shift) {
  int64_t v = (int64_t)acc * mult;
  int64_t r = (v + ((int64_t)1 << (shift - 1))) >> shift;
  if (r > 127) r = 127;
  else if (r < -128) r = -128;
  return (int8_t)r;
}

uint32_t run_workload(int iters) {
  for (int c = 0; c < CIN; c++)
    for (int y = 0; y < HH; y++)
      for (int x = 0; x < WW; x++)
        in[c][y][x] = (int8_t)(((c * 53 + y * 7 + x * 3) % 255) - 127);
  for (int o = 0; o < COUT; o++) {
    bias[o] = (o - 2) * 1000;
    for (int c = 0; c < CIN; c++)
      for (int ky = 0; ky < K; ky++)
        for (int kx = 0; kx < K; kx++)
          wt[o][c][ky][kx] = (int8_t)(((o * 11 + c * 5 + ky * 3 + kx) % 63) - 31);
  }
  const int32_t mult = 1073741824; /* 2^30 */
  const int shift = 41;

  for (int it = 0; it < iters; it++) {
    for (int o = 0; o < COUT; o++)
      for (int oy = 0; oy < OH; oy++)
        for (int ox = 0; ox < OW; ox++) {
          int32_t acc = bias[o];
          for (int c = 0; c < CIN; c++)
            for (int ky = 0; ky < K; ky++)
              for (int kx = 0; kx < K; kx++)
                acc += (int32_t)in[c][oy + ky][ox + kx] * (int32_t)wt[o][c][ky][kx];
          out[o][oy][ox] = requant(acc, mult, shift);
        }
    in[0][0][it % WW] += 1; /* vary iterations */
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, out, sizeof(out));
  TRACE_U32("conv", crc);
  return crc;
}
