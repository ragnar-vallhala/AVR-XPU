/* main.c — AHRS (1.2) harness driver: same source for host and AVR/gem5.
 * init q=identity -> run Madgwick IMU update AHRS_ITERS times on a fixed sample
 * -> trace the 4 quaternion components -> CRC over q -> halt.
 */
#include <stdint.h>

#include "harness.h"
#include "ahrs_input.h"

#ifndef AHRS_ITERS
#define AHRS_ITERS 1
#endif

void ahrs_update_imu(float q[4], float beta, float invSampleFreq,
                     float gx, float gy, float gz, float ax, float ay, float az);

int main(void) {
  float q[4] = {1.0f, 0.0f, 0.0f, 0.0f};

  for (int k = 0; k < AHRS_ITERS; k++)
    ahrs_update_imu(q, AHRS_BETA, AHRS_INVDT, AHRS_GX, AHRS_GY, AHRS_GZ,
                    AHRS_AX, AHRS_AY, AHRS_AZ);

  uint32_t crc = 0;
  for (int i = 0; i < 4; i++) {
    crc = h_crc32(crc, &q[i], 4);
#ifdef TRACE
    h_putc('q');
    h_hex32((uint32_t)i);
    h_putc(' ');
    h_hex32(h_f2u(q[i]));
    h_putc('\n');
#endif
  }
  h_finish(crc, 1);
  return 0;
}
