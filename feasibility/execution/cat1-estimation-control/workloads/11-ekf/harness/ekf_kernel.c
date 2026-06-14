/* ekf_kernel.c — standalone EKF covariance-predict microkernel.
 *
 * The body (`ekf_predict_body.inc`) is the verbatim "intermediate calculations"
 * + "covariance update" block (states 0..12: quaternion/velocity/position/gyro
 * bias) extracted from PX4 ECL covariance.cpp (lines 265-585), with only
 * `ecl::powf` -> `eclpowf`. P()/nextP() and the input scalars are provided here.
 *
 * v1 scope: states 0..12 (the always-executed core). Accel-bias (13..15),
 * magnetometer (16..21) and wind (22..23) states are TODO v2. Working set is
 * still the full 24x24 float arrays (~4.6 KB) — representative of the real cost.
 */
#include <stdint.h>

/* ecl::powf(x, n) with integer n is an exact repeated product; 1.0f*x == x in
 * IEEE-754, so this is bit-identical on host and AVR. */
static inline float eclpowf(float b, int e) {
  float r = 1.0f;
  for (int i = 0; i < e; i++)
    r *= b;
  return r;
}

void ekf_predict(const float Pin[24][24], float Pout[24][24], const float q[4],
                 const float da[3], const float dv[3], const float dab[3],
                 const float dvb[3], const float var[6], float dt) {
#define P(i, j) (Pin[i][j])
#define nextP(i, j) (Pout[i][j])
  const float q0 = q[0], q1 = q[1], q2 = q[2], q3 = q[3];
  const float dax = da[0], day = da[1], daz = da[2];
  const float dvx = dv[0], dvy = dv[1], dvz = dv[2];
  const float dax_b = dab[0], day_b = dab[1], daz_b = dab[2];
  const float dvx_b = dvb[0], dvy_b = dvb[1], dvz_b = dvb[2];
  const float daxVar = var[0], dayVar = var[1], dazVar = var[2];
  const float dvxVar = var[3], dvyVar = var[4], dvzVar = var[5];

#include "ekf_predict_body.inc"

#undef P
#undef nextP
}
