/* ekf_input.h — fixed, deterministic EKF predict inputs (no RNG, no clock).
 *
 * Non-const so they live in .data (copied to RAM at startup) — avoids AVR
 * Harvard .rodata/LPM issues under gem5. Values are arbitrary but fixed; the
 * goal is a reproducible computation that exercises the predict math, not a
 * physically meaningful filter state.
 */
#ifndef EKF_INPUT_H
#define EKF_INPUT_H

/* quaternion (small tilt), delta-angle, delta-velocity, biases, noise vars, dt */
static float EKF_Q[4] = {0.99902677f, 0.04361939f, 0.0f, 0.0f};
static float EKF_DA[3] = {0.001f, -0.002f, 0.0015f};
static float EKF_DV[3] = {0.012f, 0.020f, -0.039240f};
static float EKF_DAB[3] = {1.0e-4f, -1.0e-4f, 5.0e-5f};
static float EKF_DVB[3] = {2.0e-3f, -1.0e-3f, 3.0e-3f};
/* daxVar, dayVar, dazVar, dvxVar, dvyVar, dvzVar */
static float EKF_VAR[6] = {1.0e-6f, 1.0e-6f, 1.0e-6f, 1.0e-4f, 1.0e-4f, 1.0e-4f};
static float EKF_DT = 0.004f;

/* Deterministic symmetric initial covariance P0[i][j] (filled at runtime). */
static inline void ekf_init_P(float P[24][24]) {
  for (int i = 0; i < 24; i++)
    for (int j = 0; j < 24; j++) {
      float d = (float)((i > j) ? (i - j) : (j - i));
      P[i][j] = (i == j) ? (0.1f + 0.01f * (float)i)
                         : (0.001f * (float)(((i + j) % 5) + 1) / (1.0f + d));
    }
}

#endif /* EKF_INPUT_H */
