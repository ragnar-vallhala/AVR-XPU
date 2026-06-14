/* quat_kernel.c — quaternion / rotation glue kernels (the ops 1.1/1.2/1.4 share).
 * Plain fp32 transcription of Hamilton product, normalize (invSqrt), rotate-vec
 * and quaternion->DCM. invSqrt uses a 32-bit-int union so host and AVR agree.
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

/* Hamilton product o = a * b */
void quat_mul(const float a[4], const float b[4], float o[4]) {
  o[0] = a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3];
  o[1] = a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2];
  o[2] = a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1];
  o[3] = a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0];
}

void quat_normalize(float q[4]) {
  float n = invSqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
  q[0] *= n;  q[1] *= n;  q[2] *= n;  q[3] *= n;
}

/* rotate vector v by quaternion q: o = v + 2w(qxyz x v) + 2 qxyz x (qxyz x v) */
void quat_rotate(const float q[4], const float v[3], float o[3]) {
  float w = q[0], x = q[1], y = q[2], z = q[3];
  float tx = 2.0f * (y * v[2] - z * v[1]);
  float ty = 2.0f * (z * v[0] - x * v[2]);
  float tz = 2.0f * (x * v[1] - y * v[0]);
  o[0] = v[0] + w * tx + (y * tz - z * ty);
  o[1] = v[1] + w * ty + (z * tx - x * tz);
  o[2] = v[2] + w * tz + (x * ty - y * tx);
}

/* quaternion -> 3x3 direction cosine matrix (row-major R[9]) */
void quat_to_dcm(const float q[4], float R[9]) {
  float w = q[0], x = q[1], y = q[2], z = q[3];
  R[0] = 1.0f - 2.0f * (y * y + z * z);
  R[1] = 2.0f * (x * y - w * z);
  R[2] = 2.0f * (x * z + w * y);
  R[3] = 2.0f * (x * y + w * z);
  R[4] = 1.0f - 2.0f * (x * x + z * z);
  R[5] = 2.0f * (y * z - w * x);
  R[6] = 2.0f * (x * z - w * y);
  R[7] = 2.0f * (y * z + w * x);
  R[8] = 1.0f - 2.0f * (x * x + y * y);
}
