/* main.c — quaternion-kernels (1.3) harness: chains mul->normalize->rotate->dcm
 * each iteration (feeding the product back to avoid dead-code elimination) and
 * accumulates the results, then CRCs the accumulator.
 */
#include <stdint.h>

#include "harness.h"

#ifndef QUAT_ITERS
#define QUAT_ITERS 1
#endif

void quat_mul(const float a[4], const float b[4], float o[4]);
void quat_normalize(float q[4]);
void quat_rotate(const float q[4], const float v[3], float o[3]);
void quat_to_dcm(const float q[4], float R[9]);

int main(void) {
  float qa[4] = {0.9238795f, 0.3826834f, 0.0f, 0.0f}; /* 45 deg about x */
  float qb[4] = {0.7071068f, 0.0f, 0.7071068f, 0.0f}; /* 90 deg about y */
  float v[3] = {1.0f, 2.0f, -0.5f};
  float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};

  for (int k = 0; k < QUAT_ITERS; k++) {
    float qm[4], vr[3], R[9];
    quat_mul(qa, qb, qm);
    quat_normalize(qm);
    quat_rotate(qm, v, vr);
    quat_to_dcm(qm, R);
    acc[0] += qm[0] + qm[1] + qm[2] + qm[3];
    acc[1] += vr[0] + vr[1] + vr[2];
    for (int i = 0; i < 9; i++)
      acc[2] += R[i];
    acc[3] += qm[0];
    qa[0] = qm[0];  qa[1] = qm[1];  qa[2] = qm[2];  qa[3] = qm[3]; /* chain */
  }

  uint32_t crc = 0;
  for (int i = 0; i < 4; i++) {
    crc = h_crc32(crc, &acc[i], 4);
#ifdef TRACE
    h_putc('a');
    h_hex32((uint32_t)i);
    h_putc(' ');
    h_hex32(h_f2u(acc[i]));
    h_putc('\n');
#endif
  }
  h_finish(crc, 1);
  return 0;
}
