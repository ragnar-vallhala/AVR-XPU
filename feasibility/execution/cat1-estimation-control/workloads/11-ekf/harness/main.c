/* main.c — EKF (1.1) harness driver: same source for host reference and AVR/gem5.
 *
 * Fixed input -> run predict EKF_ITERS times -> trace checkpoints (TRACE only)
 * -> CRC32 over the states-0..12 upper triangle (the deterministic end-goal
 * signature) -> halt. Compare host vs gem5 trace+CRC to validate the gem5 run.
 */
#include <stdint.h>

#include "harness.h"
#include "ekf_input.h"

#ifndef EKF_ITERS
#define EKF_ITERS 1
#endif

void ekf_predict(const float Pin[24][24], float Pout[24][24], const float q[4],
                 const float da[3], const float dv[3], const float dab[3],
                 const float dvb[3], const float var[6], float dt);

static float P[24][24];
static float nextP[24][24];

int main(void) {
  ekf_init_P(P);
  for (int i = 0; i < 24; i++)
    for (int j = 0; j < 24; j++)
      nextP[i][j] = 0.0f;

  for (int it = 0; it < EKF_ITERS; it++) {
    ekf_predict(P, nextP, EKF_Q, EKF_DA, EKF_DV, EKF_DAB, EKF_DVB, EKF_VAR,
                EKF_DT);
    /* P := symmetric(nextP) over the written block (states 0..12) */
    for (int i = 0; i <= 12; i++)
      for (int j = i; j <= 12; j++)
        P[i][j] = P[j][i] = nextP[i][j];
  }

  /* checkpoints + end-goal CRC over the upper triangle of states 0..12 */
  uint32_t crc = 0;
  uint16_t idx = 0;
  for (int i = 0; i <= 12; i++)
    for (int j = i; j <= 12; j++) {
      float v = nextP[i][j];
      crc = h_crc32(crc, &v, 4);
#ifdef TRACE
      h_putc('P');
      h_hex32(idx);
      h_putc(' ');
      h_hex32(h_f2u(v));
      h_putc('\n');
#endif
      idx++;
    }
  h_finish(crc, 1);
  return 0;
}
