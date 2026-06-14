# §3 Baseline comparison — AVR softfloat vs ARM64 / RISC-V (HW FP)

Same C microkernels, same gem5 (ALL binary), per-invocation via i11-i1; results are
**IEEE-754 bit-identical** across all three ISAs (CRC match — the `crc` column). ARM64 =
AArch64 w/ NEON+VFP, RISC-V = RV64GC (scalar F/D), AVR = our softfloat model. `insts` =
instructions retired per kernel invocation; `AVR/ARM`,`AVR/RV` = how many MORE instructions
AVR softfloat needs.

```
workload                AVR insts  ARM insts   RV insts  AVR/ARM  AVR/RV      fp(A/Ar/Rv)  crc
12-ahrs                     16368        216        245    75.9x   66.8x   181/ 184/ 220   ok
11-ekf                     195970       4398       4600    44.6x   42.6x  2500/2161/3998   ok
13-quaternion               10396        272        278    38.2x   37.4x   145/ 130/ 230   ok
14-control-pid               6445        184        182    35.0x   35.3x    51/  96/ 128   ok
22-biquad                  187133       5583       5340    33.5x   35.0x  2162/1970/4517   ok
25-dotprod                  12520        463        466    27.0x   26.9x   131/ 131/ 263   ok
23-fft                     210060       9045      10386    23.2x   20.2x  2754/2178/4805   ok
24-matmul                   97756       4643       4133    21.1x   23.7x  1034/1034/2197   ok
15-control-allocation        4043        215        223    18.8x   18.1x    36/  47/  99   ok
21-fir                     159353       9423       8653    16.9x   18.4x  1586/2354/3821   ok
32-fc                       26579       3308       3808     8.0x    7.0x     0/   0/   0   ok
31-conv2d                  172350      23003      29080     7.5x    5.9x     0/   0/   0   ok
33-maxpool                   5201       4878       8128     1.1x    0.6x     0/   0/   0   ok
```

## Verdict
- On the fp kernels, **ARM64 needs 17-76× fewer instructions than AVR softfloat** (RISC-V similar, a bit less due to no auto-vectorisation). That is the FPU advantage: AVR turns each fp op into a ~50-170-instruction softfloat call, ARM/RISC-V do it in ~1 (NEON fuses several).
- **int8 kernels** (conv2d/fc/maxpool, fp≈0) show a smaller gap — all three do integer MACs; the AVR penalty there is only its 8-bit width, not softfloat.
- **§3 implication:** the AVR-XPU cannot beat an FPU-equipped ARM/RISC-V on raw fp instruction count — so (per the plan) its case must be **energy/area for a stripped, domain-specific datapath**, not throughput. Combined with the §2 roofline (these kernels are memory-bound once fp is in HW), the target is a **minimal fp/int8 MAC + good memory bandwidth**, competing on energy-per-op, not peak FLOPS.
- *Caveat:* gem5 ARM/RISC-V are application-class A-profile (not Cortex-M); instruction counts are robust, cycles are model-dependent. Real Cortex-M + energy = the planned hardware step.
