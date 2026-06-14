# Study Material — print pack

PDFs for the **§0.5 Study Track** in `../plan.md`. Folders match the study-track groupings.
Read the foundations folder first (it feeds §1, the entry point). Downloaded/converted June 2026.

## 01-foundations  (read before §1 Workload Characterization)
- `roofline-williams-cacm2009.pdf` — the Roofline model (Williams/Waterman/Patterson, CACM 2009). The lens for arithmetic intensity & §2.
- `px4-ekf2-guide.pdf` — PX4 ECL/EKF2 navigation-filter guide (docs.px4.io).
- `px4-ecl-covariance.cpp` — the actual EKF covariance source (24-state, single-precision, Joseph-form), kept as code. Read to confirm real op structure.

## 02-baselines  (§3 Competitive Landscape — primary baseline is ARM M55 + Helium)
- `arm-helium-optimization-guide.pdf` — combined Arm Helium (MVE) optimization docs, with figures.
- `cmsis-dsp-readme.pdf` — CMSIS-DSP (float matrix/EKF kernels).
- `cmsis-nn-readme.pdf` + `cmsis-nn-docs.pdf` — CMSIS-NN (quantized int8/int4 inference kernels; scalar/DSP/MVE variants).

## 03-isa  (§4 ISA Design — the honest RISC-V comparison)
- `riscv-v-spec-1.0.pdf` — RISC-V Vector Extension v1.0 spec (111 pp; reference, not cover-to-cover).
- `xpulpnn-arxiv-2011.14325.pdf` — XpulpNN: packed-SIMD 4b/2b ISA extension done right.
- `pulp-nn-arxiv-1908.11263.pdf` — PULP-NN: the QNN kernel methodology behind XpulpNN.

## 04-gem5  (§6 gem5 Modeling — extending your existing model)
- `gem5-v20-paper-arxiv-2007.03152.pdf` — the gem5 v20.0+ overview paper.
- `gem5-documentation.pdf` — gem5 docs landing page (index of subsystems).
- `gem5-adding-instructions.pdf` — gem5 bootcamp: adding instructions to the ISA.

## 05-fpga-anchors  (§6–§7 FPGA feasibility — open vector coprocessors that closed timing)
- `arrow-arxiv-2107.07169.pdf` — Arrow RVV-subset ML accelerator. **This is the Southampton AI-Vector-Accelerator group's paper — it is also your AVA reference** (the `ava-core` repo itself is RTL-only with a stub README, so nothing to print there).
- `ara-new-arxiv-2210.08882.pdf` — "New Ara" open RVV vector unit.

## Not included (no good printable doc)
- ASIP / Synopsys nML methodology (§5) — license-gated docs; no open PDF.
- AVA repo README — 2-line stub; superseded by the Arrow paper above.
