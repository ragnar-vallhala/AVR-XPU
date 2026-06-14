/* main.c — cascaded rate-PID (1.4) harness: 3-axis PID over a fixed setpoint
 * sequence with a simple plant feedback (so I/D terms are exercised), looped
 * PID_ITERS times; CRC over accumulated outputs + integrator state.
 */
#include <stdint.h>

#include "harness.h"

#ifndef PID_ITERS
#define PID_ITERS 1
#endif

typedef struct { float integral, prev_err; } pid_state;
float pid_step(pid_state *s, float kp, float ki, float kd, float ff,
               float setpoint, float meas, float dt, float ilim, float olim);

/* fixed setpoint sequence per axis (cycled), .data so it copies to RAM */
static float sp_seq[4][3] = {{0.10f, -0.20f, 0.05f},
                             {0.30f, 0.10f, -0.10f},
                             {-0.20f, 0.25f, 0.15f},
                             {0.00f, -0.05f, 0.20f}};

int main(void) {
  pid_state st[3] = {{0.0f, 0.0f}, {0.0f, 0.0f}, {0.0f, 0.0f}};
  float meas[3] = {0.0f, 0.0f, 0.0f};
  float acc[3] = {0.0f, 0.0f, 0.0f};
  const float kp = 0.15f, ki = 0.2f, kd = 0.003f, ff = 0.05f;
  const float dt = 0.001f, ilim = 0.3f, olim = 1.0f;

  for (int k = 0; k < PID_ITERS; k++) {
    float *sp = sp_seq[k & 3];
    for (int a = 0; a < 3; a++) {
      float u = pid_step(&st[a], kp, ki, kd, ff, sp[a], meas[a], dt, ilim, olim);
      acc[a] += u;
      meas[a] += 0.1f * u; /* simple plant so meas evolves */
    }
  }

  uint32_t crc = 0;
  for (int a = 0; a < 3; a++) {
    crc = h_crc32(crc, &acc[a], 4);
#ifdef TRACE
    h_putc('u');
    h_hex32((uint32_t)a);
    h_putc(' ');
    h_hex32(h_f2u(acc[a]));
    h_putc('\n');
#endif
  }
  for (int a = 0; a < 3; a++)
    crc = h_crc32(crc, &st[a].integral, 4);
  h_finish(crc, 1);
  return 0;
}
