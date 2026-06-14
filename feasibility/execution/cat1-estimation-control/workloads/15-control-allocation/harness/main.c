/* main.c — control allocation (1.5) harness: quad-X effectiveness pseudo-inverse
 * times a fixed setpoint sequence (some driving actuators into saturation),
 * looped ALLOC_ITERS times; CRC over accumulated actuator outputs.
 */
#include <stdint.h>

#include "harness.h"

#ifndef ALLOC_ITERS
#define ALLOC_ITERS 1
#endif

void allocate(const float Bpinv[4][4], const float sp[4], float u[4],
              float umin, float umax);

/* quad-X mixer pseudo-inverse: rows=motors, cols=[roll, pitch, yaw, thrust] */
static float Bpinv[4][4] = {{-0.25f, 0.25f, 0.25f, 0.25f},
                            {0.25f, -0.25f, 0.25f, 0.25f},
                            {0.25f, 0.25f, -0.25f, 0.25f},
                            {-0.25f, -0.25f, -0.25f, 0.25f}};
/* fixed setpoint sequence [roll, pitch, yaw, thrust]; some saturate */
static float sp_seq[4][4] = {{0.2f, 0.1f, -0.05f, 0.6f},
                             {0.9f, -0.8f, 0.3f, 0.9f},
                             {-0.4f, 0.5f, -0.6f, 0.5f},
                             {0.1f, 0.1f, 0.1f, 1.0f}};

int main(void) {
  float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
  for (int k = 0; k < ALLOC_ITERS; k++) {
    float u[4];
    allocate(Bpinv, sp_seq[k & 3], u, 0.0f, 1.0f);
    for (int i = 0; i < 4; i++)
      acc[i] += u[i];
  }

  uint32_t crc = 0;
  for (int i = 0; i < 4; i++) {
    crc = h_crc32(crc, &acc[i], 4);
#ifdef TRACE
    h_putc('u');
    h_hex32((uint32_t)i);
    h_putc(' ');
    h_hex32(h_f2u(acc[i]));
    h_putc('\n');
#endif
  }
  h_finish(crc, 1);
  return 0;
}
