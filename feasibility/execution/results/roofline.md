# §2 Roofline analysis (from measured run-logs)

Per-invocation kernel work isolated via the **i11 − i1 difference** (cancels startup).
Model: AVR data-memory `MEM_BW = 0.5 byte/cycle` (LD/ST ~2 cyc/byte); HW-arith compute roof
`W ops/cycle` at SIMD width W; memory↔compute ridge at intensity `I = 2W ops/byte`.
`bytes` = LD/ST count (softfloat-inclusive ⇒ a *conservative*, low intensity; a lean HW-fp
core moves fewer bytes ⇒ even more compute-bound). `sp@W` = attainable speedup over the
softfloat baseline at SIMD width W.

```
workload               kind   ops/inv   bytes  cyc/op  I(op/B) helper% ridgeW   sp@1   sp@4   sp@8
32-fc                  int8      2048    3338    20.0     0.61   58.5%    0.3    6.1    6.1    6.1
31-conv2d              int8     10368   19738    24.1     0.53   59.1%    0.3    6.3    6.3    6.3
12-ahrs                fp         181     680   123.9     0.27   98.2%    0.1   16.5   16.5   16.5
25-dotprod             fp         131     528   131.1     0.25   83.8%    0.1   16.3   16.3   16.3
24-matmul              fp        1034    4644   130.7     0.22   83.5%    0.1   14.6   14.6   14.6
11-ekf                 fp        2500   12788   110.5     0.20   97.8%    0.1   10.8   10.8   10.8
21-fir                 fp        1586    8254   137.5     0.19   79.0%    0.1   13.2   13.2   13.2
13-quaternion          fp         145     806   103.9     0.18   85.0%    0.1    9.3    9.3    9.3
22-biquad              fp        2162   19316   123.2     0.11   85.8%    0.1    6.9    6.9    6.9
23-fft                 fp        2754   25292   109.9     0.11   77.1%    0.1    6.0    6.0    6.0
15-control-allocation  fp          36     332   157.3     0.11   77.5%    0.1    8.5    8.5    8.5
14-control-pid         fp          51     603   173.4     0.08   90.9%    0.0    7.3    7.3    7.3
```

## Verdict

1. **Baseline = compute(softfloat)-bound.** 58–98% of cycles are in arithmetic helper routines, at ~100–170 cycles per fp op. A scalar HW fp/MAC datapath removes that tax — **≈ 6–16× speedup** (the `sp@1` column).
2. **But arithmetic intensity is LOW** (0.08–0.61 op/byte) — far *left* of the scalar ridge (2 op/byte). So once arithmetic is in hardware the kernels become **memory-bound**: every `ridgeW < 1`, and `sp@1 == sp@4 == sp@8` — **wide SIMD does NOT help.** The ceiling is set by memory bandwidth, not compute.
3. **Design implication:** prioritise a HW fp/MAC datapath **+ more memory bandwidth** (wider / multi-byte loads, a local scratchpad) over many vector lanes. The §1/§2 memory-bound kill-criterion *does* bite — it kills *wide SIMD*, but **not** the HW-arithmetic datapath, which still delivers the 6–16×.
4. *Caveat:* `bytes` = LD/ST count; for the big-expression EKF some are register spills (a fp core may spill too), so per-kernel intensity is approximate — but the **order-of-magnitude (intensity ≪ ridge) conclusion is robust** across all kernels.
5. `33-maxpool` is excluded: no MAC (pure int8 compares) — nothing for an arithmetic datapath to offload; it is load/compare-bound.
