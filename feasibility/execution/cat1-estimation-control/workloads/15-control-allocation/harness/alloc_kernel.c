/* alloc_kernel.c — control allocation: u = clamp(B+ . setpoint).
 * Dense (n_act x 4) pseudo-inverse times the [tau; T] control setpoint, then
 * per-actuator saturation. Structurally a small dense fp32 mat-vec MAC + clamp
 * (the same MAC primitive as Cat-2 mat-mult, at tiny size).
 */
void allocate(const float Bpinv[4][4], const float sp[4], float u[4],
              float umin, float umax) {
  for (int i = 0; i < 4; i++) {
    float s = 0.0f;
    for (int j = 0; j < 4; j++)
      s += Bpinv[i][j] * sp[j];
    if (s > umax)
      s = umax;
    else if (s < umin)
      s = umin;
    u[i] = s;
  }
}
