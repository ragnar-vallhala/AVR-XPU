/* ahrs_kernel.c — Madgwick AHRS 6-axis (IMU) update, standalone microkernel.
 *
 * Transcribed from MadgwickAHRS.cpp (updateIMU), operating on a float q[4]
 * instead of member state. Pure fp32 + the fast inverse-sqrt bit hack, no libm
 * (so it is bit-identical on host and AVR). NOTE: the original invSqrt uses
 * `*(long*)&y`, which is 64-bit on x86-64 host and would mis-pun there; fixed to
 * a 32-bit int union so host and AVR agree bit-for-bit.
 */
#include <stdint.h>

static inline float invSqrt(float x) {
  float halfx = 0.5f * x;
  union { float f; int32_t i; } u;
  u.f = x;
  u.i = 0x5f3759df - (u.i >> 1);
  float y = u.f;
  y = y * (1.5f - (halfx * y * y));
  y = y * (1.5f - (halfx * y * y));
  return y;
}

void ahrs_update_imu(float q[4], float beta, float invSampleFreq,
                     float gx, float gy, float gz,
                     float ax, float ay, float az) {
  float q0 = q[0], q1 = q[1], q2 = q[2], q3 = q[3];
  float recipNorm, s0, s1, s2, s3, qDot1, qDot2, qDot3, qDot4;
  float _2q0, _2q1, _2q2, _2q3, _4q0, _4q1, _4q2, _8q1, _8q2, q0q0, q1q1, q2q2, q3q3;

  gx *= 0.0174533f;
  gy *= 0.0174533f;
  gz *= 0.0174533f;

  qDot1 = 0.5f * (-q1 * gx - q2 * gy - q3 * gz);
  qDot2 = 0.5f * (q0 * gx + q2 * gz - q3 * gy);
  qDot3 = 0.5f * (q0 * gy - q1 * gz + q3 * gx);
  qDot4 = 0.5f * (q0 * gz + q1 * gy - q2 * gx);

  if (!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {
    recipNorm = invSqrt(ax * ax + ay * ay + az * az);
    ax *= recipNorm;
    ay *= recipNorm;
    az *= recipNorm;

    _2q0 = 2.0f * q0;  _2q1 = 2.0f * q1;  _2q2 = 2.0f * q2;  _2q3 = 2.0f * q3;
    _4q0 = 4.0f * q0;  _4q1 = 4.0f * q1;  _4q2 = 4.0f * q2;
    _8q1 = 8.0f * q1;  _8q2 = 8.0f * q2;
    q0q0 = q0 * q0;  q1q1 = q1 * q1;  q2q2 = q2 * q2;  q3q3 = q3 * q3;

    s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;
    s1 = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * q1 - _2q0 * ay - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;
    s2 = 4.0f * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;
    s3 = 4.0f * q1q1 * q3 - _2q1 * ax + 4.0f * q2q2 * q3 - _2q2 * ay;
    recipNorm = invSqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
    s0 *= recipNorm;  s1 *= recipNorm;  s2 *= recipNorm;  s3 *= recipNorm;

    qDot1 -= beta * s0;  qDot2 -= beta * s1;  qDot3 -= beta * s2;  qDot4 -= beta * s3;
  }

  q0 += qDot1 * invSampleFreq;
  q1 += qDot2 * invSampleFreq;
  q2 += qDot3 * invSampleFreq;
  q3 += qDot4 * invSampleFreq;

  recipNorm = invSqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
  q0 *= recipNorm;  q1 *= recipNorm;  q2 *= recipNorm;  q3 *= recipNorm;

  q[0] = q0;  q[1] = q1;  q[2] = q2;  q[3] = q3;
}
