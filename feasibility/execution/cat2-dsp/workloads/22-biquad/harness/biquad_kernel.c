/* biquad_kernel.c — fp32 biquad IIR cascade, Direct Form 1
 * (CMSIS arm_biquad_cascade_df1_f32 scalar form).
 * per section: y = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2; sections chained. */
#include <stdint.h>
#include "harness.h"

#define NSEC 4
#define BLK 48
/* per-section coeffs {b0,b1,b2,a1,a2} and state {x1,x2,y1,y2} */
static float coef[NSEC][5], state[NSEC][4], x[BLK];

uint32_t run_workload(int iters) {
  for (int s = 0; s < NSEC; s++) {
    coef[s][0] = 0.2f; coef[s][1] = 0.4f; coef[s][2] = 0.2f;
    coef[s][3] = -0.3f + 0.05f * (float)s; coef[s][4] = 0.1f;
    state[s][0] = state[s][1] = state[s][2] = state[s][3] = 0.0f;
  }
  for (int n = 0; n < BLK; n++)
    x[n] = 0.1f * (float)((n % 9) - 4);

  float acc = 0.0f;
  for (int it = 0; it < iters; it++) {
    for (int n = 0; n < BLK; n++) {
      float in = x[n];
      for (int s = 0; s < NSEC; s++) {
        float *c = coef[s], *st = state[s];
        float out = c[0] * in + c[1] * st[0] + c[2] * st[1] - c[3] * st[2] - c[4] * st[3];
        st[1] = st[0]; st[0] = in;     /* x2=x1; x1=in */
        st[3] = st[2]; st[2] = out;    /* y2=y1; y1=out */
        in = out;                      /* feed to next section */
      }
      acc += in;
    }
    x[it % BLK] += 1e-4f * acc;
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, &acc, 4);
  TRACE_F32("biq", acc);
  return crc;
}
