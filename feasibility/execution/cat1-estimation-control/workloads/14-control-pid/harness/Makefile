# PID (1.4) harness — host reference + AVR/gem5 build, with/without TRACE.
HARNESS := ../../../../harness
MCU     := atmega1284p
RODATA  := 0x802000
ITERS   ?= 1

CC_HOST  := gcc
CC_AVR   := avr-gcc
FPFLAGS  := -ffp-contract=off -fno-fast-math
CFLAGS   := -O2 -Wall -I. -I$(HARNESS) $(FPFLAGS) -DPID_ITERS=$(ITERS)
AVRFLAGS := -O1 -mmcu=$(MCU) -I. -I$(HARNESS) $(FPFLAGS) -DPID_ITERS=$(ITERS) \
            -Wl,--section-start,.rodata=$(RODATA)
SRCS := main.c pid_kernel.c

.PHONY: all host host-trace avr avr-trace clean
all: host avr
host:       ; $(CC_HOST) $(CFLAGS)           $(SRCS) -o pid_host
host-trace: ; $(CC_HOST) $(CFLAGS) -DTRACE   $(SRCS) -o pid_host_trace
avr:        ; $(CC_AVR)  $(AVRFLAGS)         $(SRCS) -o pid_avr.elf
avr-trace:  ; $(CC_AVR)  $(AVRFLAGS) -DTRACE $(SRCS) -o pid_avr_trace.elf
clean:      ; rm -f pid_host pid_host_trace pid_avr.elf pid_avr_trace.elf
