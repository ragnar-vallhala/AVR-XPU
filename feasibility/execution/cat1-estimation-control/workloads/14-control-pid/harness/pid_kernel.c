/* pid_kernel.c — one rate-PID control step: P + I (anti-windup clamp) + D
 * (with feedforward and output saturation). Plain fp32; the clamps make it
 * branch-heavier than the other Cat-1 kernels, and the D term has a division.
 */
typedef struct { float integral, prev_err; } pid_state;

float pid_step(pid_state *s, float kp, float ki, float kd, float ff,
               float setpoint, float meas, float dt, float ilim, float olim) {
  float err = setpoint - meas;
  float p = kp * err;
  s->integral += ki * err * dt;
  if (s->integral > ilim)
    s->integral = ilim;
  else if (s->integral < -ilim)
    s->integral = -ilim;
  float d = kd * (err - s->prev_err) / dt;
  s->prev_err = err;
  float out = p + s->integral + d + ff * setpoint;
  if (out > olim)
    out = olim;
  else if (out < -olim)
    out = -olim;
  return out;
}
