/* wl_main.c — generic workload driver. Each workload provides run_workload(),
 * which runs the kernel ITERS times and returns a CRC over its output (emitting
 * TRACE checkpoints when TRACE is defined). Keeps per-workload code to one file.
 */
#include <stdint.h>

#include "harness.h"

#ifndef ITERS
#define ITERS 1
#endif

uint32_t run_workload(int iters);

int main(void) {
  h_finish(run_workload(ITERS), 1);
  return 0;
}
