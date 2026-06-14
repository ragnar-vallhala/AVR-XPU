# control allocation (1.5) harness — host reference + AVR/gem5 build.
HARNESS := ../../../../harness
MCU     := atmega1284p
RODATA  := 0x802000
ITERS   ?= 1

CC_HOST  := gcc
CC_AVR   := avr-gcc
FPFLAGS  := -ffp-contract=off -fno-fast-math
CFLAGS   := -O2 -Wall -I. -I$(HARNESS) $(FPFLAGS) -DALLOC_ITERS=$(ITERS)
AVRFLAGS := -O1 -mmcu=$(MCU) -I. -I$(HARNESS) $(FPFLAGS) -DALLOC_ITERS=$(ITERS) \
            -Wl,--section-start,.rodata=$(RODATA)
SRCS := main.c alloc_kernel.c

.PHONY: all host host-trace avr avr-trace clean
all: host avr
host:       ; $(CC_HOST) $(CFLAGS)           $(SRCS) -o alloc_host
host-trace: ; $(CC_HOST) $(CFLAGS) -DTRACE   $(SRCS) -o alloc_host_trace
avr:        ; $(CC_AVR)  $(AVRFLAGS)         $(SRCS) -o alloc_avr.elf
avr-trace:  ; $(CC_AVR)  $(AVRFLAGS) -DTRACE $(SRCS) -o alloc_avr_trace.elf
clean:      ; rm -f alloc_host alloc_host_trace alloc_avr.elf alloc_avr_trace.elf
