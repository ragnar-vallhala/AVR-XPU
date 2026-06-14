/* ahrs_input.h — fixed deterministic IMU sample + filter params (Madgwick). */
#ifndef AHRS_INPUT_H
#define AHRS_INPUT_H

/* one fixed IMU reading, applied every update step (deterministic) */
#define AHRS_GX 12.5f      /* gyro deg/s */
#define AHRS_GY (-7.25f)
#define AHRS_GZ 3.0f
#define AHRS_AX 0.20f      /* accel (un-normalized; kernel normalizes) */
#define AHRS_AY 0.05f
#define AHRS_AZ 9.78f
#define AHRS_BETA 0.1f
#define AHRS_INVDT (1.0f / 512.0f)   /* 512 Hz sample period */

#endif /* AHRS_INPUT_H */
