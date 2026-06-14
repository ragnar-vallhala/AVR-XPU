# generic workload Makefile — builds the single *_kernel.c in this dir against
# the shared wl_main.c driver, host + AVR/gem5, with/without TRACE.
HARNESS := ../../../../harness
MCU     := atmega1284p
RODATA  := 0x802000
ITERS   ?= 1

CC_HOST  := gcc
CC_AVR   := avr-gcc
FPFLAGS  := -ffp-contract=off -fno-fast-math
CFLAGS   := -O2 -Wall -I. -I$(HARNESS) $(FPFLAGS) -DITERS=$(ITERS)
AVRFLAGS := -O1 -mmcu=$(MCU) -I. -I$(HARNESS) $(FPFLAGS) -DITERS=$(ITERS) \
            -Wl,--section-start,.rodata=$(RODATA)
KERNEL := $(wildcard *_kernel.c)
NAME   := $(patsubst %_kernel.c,%,$(KERNEL))
SRCS   := $(HARNESS)/wl_main.c $(KERNEL)

.PHONY: all host host-trace avr avr-trace clean
all: host avr
host:       ; $(CC_HOST) $(CFLAGS)           $(SRCS) -o $(NAME)_host
host-trace: ; $(CC_HOST) $(CFLAGS) -DTRACE   $(SRCS) -o $(NAME)_host_trace
avr:        ; $(CC_AVR)  $(AVRFLAGS)         $(SRCS) -o $(NAME)_avr.elf
avr-trace:  ; $(CC_AVR)  $(AVRFLAGS) -DTRACE $(SRCS) -o $(NAME)_avr.elf
clean:      ; rm -f *_host *_host_trace *_avr.elf
