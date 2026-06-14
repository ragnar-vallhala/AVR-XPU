/* harness.h — shared, portable harness primitives for Cat-1..3 workloads.
 *
 * One source compiles two ways:
 *   - host  (gcc/x86-64): output via stdio, halt via exit().
 *   - AVR   (avr-gcc, run on gem5): output via the gem5 SE break-syscall ABI
 *           (r16=1 putchar(r17); r16=2 exit), see src/arch/avr/faults.cc.
 *
 * Trace = per-checkpoint lines "<id> <8-hex IEEE-754>" emitted ONLY when TRACE
 * is defined; read-only snapshots, so the kernel's data/flow are unchanged.
 * Compare host vs gem5 traces (and the final CRC) to validate a gem5 run.
 */
#ifndef HARNESS_H
#define HARNESS_H
#include <stdint.h>

/* ---- platform output primitive ---------------------------------------- */
#if defined(__AVR__)
static inline void h_putc(char c) {
  __asm__ __volatile__("mov r17, %0\n\t"
                       "ldi r16, 1\n\t"
                       "break\n\t" ::"r"(c)
                       : "r16", "r17");
}
static inline void h_halt(void) {
  __asm__ __volatile__("ldi r16, 2\n\t"
                       "break\n\t" ::: "r16");
  for (;;) {
  } /* not reached: gem5 exits the sim loop on the break-exit syscall */
}
#else
#include <stdio.h>
#include <stdlib.h>
static inline void h_putc(char c) { putchar(c); }
static inline void h_halt(void) {
  fflush(stdout);
  exit(0);
}
#endif

static inline void h_puts(const char *s) {
  while (*s)
    h_putc(*s++);
}

static inline void h_hex32(uint32_t v) {
  static const char hx[] = "0123456789abcdef";
  for (int i = 7; i >= 0; i--)
    h_putc(hx[(v >> (i * 4)) & 0xF]);
}

/* read-only reinterpret of a float as its IEEE-754 bit pattern */
static inline uint32_t h_f2u(float f) {
  union {
    float f;
    uint32_t u;
  } t;
  t.f = f;
  return t.u;
}

/* ---- trace API (compiled out entirely unless TRACE) ------------------- */
#ifdef TRACE
#define TRACE_F32(id, fv)                                                      \
  do {                                                                         \
    h_puts(id);                                                                \
    h_putc(' ');                                                               \
    h_hex32(h_f2u(fv));                                                        \
    h_putc('\n');                                                              \
  } while (0)
#define TRACE_U32(id, uv)                                                      \
  do {                                                                         \
    h_puts(id);                                                                \
    h_putc(' ');                                                               \
    h_hex32((uint32_t)(uv));                                                   \
    h_putc('\n');                                                              \
  } while (0)
#define TRACE_ON 1
#else
#define TRACE_F32(id, fv)                                                      \
  do {                                                                         \
  } while (0)
#define TRACE_U32(id, uv)                                                      \
  do {                                                                         \
  } while (0)
#define TRACE_ON 0
#endif

/* ---- CRC32 (bitwise, table-free, deterministic) ----------------------- */
static inline uint32_t h_crc32(uint32_t crc, const void *buf, uint16_t n) {
  const uint8_t *p = (const uint8_t *)buf;
  crc = ~crc;
  for (uint16_t i = 0; i < n; i++) {
    crc ^= p[i];
    for (uint8_t k = 0; k < 8; k++)
      crc = (crc >> 1) ^ (0xEDB88320u & (uint32_t)(-(int32_t)(crc & 1)));
  }
  return ~crc;
}

/* ---- end-goal signature + clean halt ---------------------------------- */
static inline void h_finish(uint32_t crc, int pass) {
  h_puts("CRC ");
  h_hex32(crc);
  h_putc('\n');
  h_puts(pass ? "PASS\n" : "FAIL\n");
  h_halt();
}

#endif /* HARNESS_H */
