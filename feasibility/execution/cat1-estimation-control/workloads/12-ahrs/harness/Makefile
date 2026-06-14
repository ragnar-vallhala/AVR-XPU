# AHRS (1.2) harness — host reference + AVR/gem5 build, with/without TRACE.
HARNESS := ../../../../harness
MCU     := atmega1284p
RODATA  := 0x802000
ITERS   ?= 1

CC_HOST  := gcc
CC_AVR   := avr-gcc
FPFLAGS  := -ffp-contract=off -fno-fast-math
CFLAGS   := -O2 -Wall -I. -I$(HARNESS) $(FPFLAGS) -DAHRS_ITERS=$(ITERS)
AVRFLAGS := -O1 -mmcu=$(MCU) -I. -I$(HARNESS) $(FPFLAGS) -DAHRS_ITERS=$(ITERS) \
            -Wl,--section-start,.rodata=$(RODATA)
SRCS := main.c ahrs_kernel.c

.PHONY: all host host-trace avr avr-trace clean
all: host avr
host:       ; $(CC_HOST) $(CFLAGS)           $(SRCS) -o ahrs_host
host-trace: ; $(CC_HOST) $(CFLAGS) -DTRACE   $(SRCS) -o ahrs_host_trace
avr:        ; $(CC_AVR)  $(AVRFLAGS)         $(SRCS) -o ahrs_avr.elf
avr-trace:  ; $(CC_AVR)  $(AVRFLAGS) -DTRACE $(SRCS) -o ahrs_avr_trace.elf
clean:      ; rm -f ahrs_host ahrs_host_trace ahrs_avr.elf ahrs_avr_trace.elf
