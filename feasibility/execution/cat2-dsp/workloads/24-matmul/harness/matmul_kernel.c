/* matmul_kernel.c — fp32 dense matrix multiply C = A*B (CMSIS arm_mat_mult_f32
 * scalar form). The MxKxN MAC primitive shared by EKF-update and MPC. */
#include <stdint.h>
#include "harness.h"

#define M 8
#define K 8
#define NN 8
static float A[M][K], B[K][NN], C[M][NN];

uint32_t run_workload(int iters) {
  for (int i = 0; i < M; i++)
    for (int j = 0; j < K; j++)
      A[i][j] = 0.05f * (float)(((i * K + j) % 13) - 6);
  for (int i = 0; i < K; i++)
    for (int j = 0; j < NN; j++)
      B[i][j] = 0.05f * (float)(((i * NN + j) % 11) - 5);

  float acc = 0.0f;
  for (int it = 0; it < iters; it++) {
    for (int i = 0; i < M; i++)
      for (int j = 0; j < NN; j++) {
        float s = 0.0f;
        for (int l = 0; l < K; l++)
          s += A[i][l] * B[l][j];
        C[i][j] = s;
      }
    for (int i = 0; i < M; i++)
      acc += C[i][i]; /* trace(C) */
    A[it % M][it % K] += 1e-4f * acc;
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, &acc, 4);
  TRACE_F32("mm", acc);
  return crc;
}
