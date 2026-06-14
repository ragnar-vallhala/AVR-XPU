# quaternion (1.3) harness — host reference + AVR/gem5 build, with/without TRACE.
HARNESS := ../../../../harness
MCU     := atmega1284p
RODATA  := 0x802000
ITERS   ?= 1

CC_HOST  := gcc
CC_AVR   := avr-gcc
FPFLAGS  := -ffp-contract=off -fno-fast-math
CFLAGS   := -O2 -Wall -I. -I$(HARNESS) $(FPFLAGS) -DQUAT_ITERS=$(ITERS)
AVRFLAGS := -O1 -mmcu=$(MCU) -I. -I$(HARNESS) $(FPFLAGS) -DQUAT_ITERS=$(ITERS) \
            -Wl,--section-start,.rodata=$(RODATA)
SRCS := main.c quat_kernel.c

.PHONY: all host host-trace avr avr-trace clean
all: host avr
host:       ; $(CC_HOST) $(CFLAGS)           $(SRCS) -o quat_host
host-trace: ; $(CC_HOST) $(CFLAGS) -DTRACE   $(SRCS) -o quat_host_trace
avr:        ; $(CC_AVR)  $(AVRFLAGS)         $(SRCS) -o quat_avr.elf
avr-trace:  ; $(CC_AVR)  $(AVRFLAGS) -DTRACE $(SRCS) -o quat_avr_trace.elf
clean:      ; rm -f quat_host quat_host_trace quat_avr.elf quat_avr_trace.elf
