# EKF (1.1) harness — host reference + AVR/gem5 build, with/without TRACE.
#   make host        host-trace        -> ekf_host[_trace]
#   make avr         avr-trace         -> ekf_avr[_trace].elf  (run on gem5 build/AVR/gem5.opt)
#   make ITERS=11 avr                  -> EKF_ITERS=11 build (two-run difference for op-mix)
HARNESS := ../../../../harness
MCU     := atmega1284p   # 16 KB SRAM: the 24x24 fp32 working set (~4.6 KB) won't fit a 328P's 2 KB
RODATA  := 0x802000      # place .rodata in data space so gem5 flat-memory loads read it correctly
ITERS   ?= 1

CC_HOST  := gcc
CC_AVR   := avr-gcc
FPFLAGS  := -ffp-contract=off -fno-fast-math          # deterministic IEEE-754 single, no contraction
CFLAGS   := -O2 -Wall -I. -I$(HARNESS) $(FPFLAGS) -DEKF_ITERS=$(ITERS)
AVRFLAGS := -O1 -mmcu=$(MCU) -I. -I$(HARNESS) $(FPFLAGS) -DEKF_ITERS=$(ITERS) \
            -Wl,--section-start,.rodata=$(RODATA)
SRCS := main.c ekf_kernel.c

.PHONY: all host host-trace avr avr-trace clean
all: host avr

host:       ; $(CC_HOST) $(CFLAGS)           $(SRCS) -o ekf_host
host-trace: ; $(CC_HOST) $(CFLAGS) -DTRACE   $(SRCS) -o ekf_host_trace
avr:        ; $(CC_AVR)  $(AVRFLAGS)         $(SRCS) -o ekf_avr.elf
avr-trace:  ; $(CC_AVR)  $(AVRFLAGS) -DTRACE $(SRCS) -o ekf_avr_trace.elf
clean:      ; rm -f ekf_host ekf_host_trace ekf_avr.elf ekf_avr_trace.elf
