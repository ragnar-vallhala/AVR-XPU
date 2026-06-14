/* maxpool_kernel.c — int8 2x2 max pooling (CMSIS-NN arm_max_pool_s8 form).
 * out = max over each 2x2 window. Integer compares only (no MAC, no requant) —
 * the cheapest inference op, a useful contrast. */
#include <stdint.h>
#include "harness.h"

#define C 4
#define HH 16
#define WW 16
#define P 2
#define OH (HH / P)
#define OW (WW / P)
static int8_t in[C][HH][WW];
static int8_t out[C][OH][OW];

uint32_t run_workload(int iters) {
  for (int c = 0; c < C; c++)
    for (int y = 0; y < HH; y++)
      for (int x = 0; x < WW; x++)
        in[c][y][x] = (int8_t)(((c * 29 + y * 11 + x * 7) % 255) - 127);

  for (int it = 0; it < iters; it++) {
    for (int c = 0; c < C; c++)
      for (int oy = 0; oy < OH; oy++)
        for (int ox = 0; ox < OW; ox++) {
          int8_t m = -128;
          for (int py = 0; py < P; py++)
            for (int px = 0; px < P; px++) {
              int8_t v = in[c][oy * P + py][ox * P + px];
              if (v > m)
                m = v;
            }
          out[c][oy][ox] = m;
        }
    in[0][0][it % WW] += 1;
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, out, sizeof(out));
  TRACE_U32("pool", crc);
  return crc;
}
