/* fft_kernel.c — radix-2 DIT Cooley-Tukey FFT, N=64 (CMSIS arm_rfft/cfft family).
 * Distinct DSP profile: bit-reversal + complex butterflies over a precomputed
 * twiddle table (float literals => bit-identical host/AVR, no runtime sin/cos). */
#include <stdint.h>
#include "harness.h"

#define N 64
#define LOGN 6
static float Wre[N/2] = {1.0f, 0.995184727f, 0.98078528f, 0.956940336f, 0.923879533f, 0.881921264f, 0.831469612f, 0.773010453f, 0.707106781f, 0.634393284f, 0.555570233f, 0.471396737f, 0.382683432f, 0.290284677f, 0.195090322f, 0.0980171403f, 6.123234e-17f, -0.0980171403f, -0.195090322f, -0.290284677f, -0.382683432f, -0.471396737f, -0.555570233f, -0.634393284f, -0.707106781f, -0.773010453f, -0.831469612f, -0.881921264f, -0.923879533f, -0.956940336f, -0.98078528f, -0.995184727f};
static float Wim[N/2] = {-0.0f, -0.0980171403f, -0.195090322f, -0.290284677f, -0.382683432f, -0.471396737f, -0.555570233f, -0.634393284f, -0.707106781f, -0.773010453f, -0.831469612f, -0.881921264f, -0.923879533f, -0.956940336f, -0.98078528f, -0.995184727f, -1.0f, -0.995184727f, -0.98078528f, -0.956940336f, -0.923879533f, -0.881921264f, -0.831469612f, -0.773010453f, -0.707106781f, -0.634393284f, -0.555570233f, -0.471396737f, -0.382683432f, -0.290284677f, -0.195090322f, -0.0980171403f};
static float xin[N], re[N], im[N];

static int bitrev(int x) {
  int r = 0;
  for (int b = 0; b < LOGN; b++) { r = (r << 1) | (x & 1); x >>= 1; }
  return r;
}

uint32_t run_workload(int iters) {
  for (int i = 0; i < N; i++)
    xin[i] = 0.1f * (float)((i % 13) - 6);

  float acc = 0.0f;
  for (int it = 0; it < iters; it++) {
    for (int i = 0; i < N; i++) { re[bitrev(i)] = xin[i]; im[i] = 0.0f; }
    for (int len = 2; len <= N; len <<= 1) {
      int half = len >> 1, step = N / len;
      for (int i = 0; i < N; i += len)
        for (int j = 0; j < half; j++) {
          int wk = j * step;
          float wr = Wre[wk], wi = Wim[wk];
          float tr = wr * re[i+j+half] - wi * im[i+j+half];
          float ti = wr * im[i+j+half] + wi * re[i+j+half];
          re[i+j+half] = re[i+j] - tr; im[i+j+half] = im[i+j] - ti;
          re[i+j] += tr;               im[i+j] += ti;
        }
    }
    for (int i = 0; i < N; i++) acc += re[i]*re[i] + im[i]*im[i];
    xin[it % N] += 1e-4f * acc;
  }
  uint32_t crc = 0;
  crc = h_crc32(crc, &acc, 4);
  TRACE_F32("fft", acc);
  return crc;
}
