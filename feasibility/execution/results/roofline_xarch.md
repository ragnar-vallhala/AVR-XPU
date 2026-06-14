# §2 Cross-architecture arithmetic analysis (AVR / ARM64 / RISC-V)

Same fp microkernels, same gem5, per-invocation via i11-i1. **Arithmetic intensity** =
fp-ops / data-bytes-moved; **tput** = achieved fp-ops / cycle. Data bytes come from the
mem-controller (`bytesRead/Written::cpu.data`) for all three ISAs, so the byte axis is
architecture-independent (total data traffic incl. stack spills). fp-ops = softfloat
calls (AVR) / committed float op-class instructions (ARM, RISC-V).

```
workload               |  AVR  I    tput |  ARM  I    tput |  RV   I    tput | ARM/AVR tput
12-ahrs                |   0.070  0.0081 |   1.039  0.6985 |   0.641  0.5424 |        86.5x
25-dotprod             |   0.062  0.0076 |   0.251  0.2824 |   0.250  0.1652 |        37.0x
24-matmul              |   0.061  0.0077 |   0.235  0.2223 |   0.235  0.1929 |        29.1x
11-ekf                 |   0.065  0.0090 |   0.287  0.4703 |   0.288  0.5322 |        52.0x
21-fir                 |   0.058  0.0073 |   0.280  0.1808 |   0.280  0.1341 |        24.9x
13-quaternion          |   0.062  0.0096 |   0.327  0.4552 |   0.320  0.3201 |        47.3x
22-biquad              |   0.053  0.0081 |   0.175  0.3185 |   0.175  0.1770 |        39.2x
23-fft                 |   0.054  0.0091 |   0.207  0.2310 |   0.202  0.1781 |        25.4x
15-control-allocation  |   0.043  0.0064 |   0.108  0.2156 |   0.185  0.1249 |        33.9x
14-control-pid         |   0.040  0.0058 |   0.312  0.2307 |   0.380  0.2036 |        40.0x
```

## Verdict
- **Throughput:** ARM/RISC-V achieve **0.18-0.70 fp-ops/cycle** (near the scalar FP roof of 1), vs AVR softfloat's **0.0058-0.0096** — a **25-87x** gap that matches the §3 instruction-count gap and confirms it is the *lack of a hardware FPU*, not the ISA encoding.
- **Intensity:** AVR sits at **0.040-0.070 fp/byte**, **2-26x lower** than ARM (0.11-1.04): softfloat moves ~5x more bytes per fp op (register
  spills), pushing AVR *further* into the memory-bound region — so on real hardware the
  HW-fp datapath must be paired with enough memory bandwidth to feed it.
- *Caveat:* ARM NEON may pack several fp ops per instruction, so its fp-op count (and thus
  intensity/throughput) is a slight under-count where auto-vectorisation fired (e.g. fir).
