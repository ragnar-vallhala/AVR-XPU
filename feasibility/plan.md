# Feasibility Study Plan: AVR-Derived SIMD Coprocessor for Edge Inference

**Project codename:** (TBD) — an AVR-ISA-derived SIMD core targeting EKF / DSP / lightweight-inference offload for drone flight control, validated in gem5, with an FPGA rollout as the proof-of-concept target.

**Author:** Ashutosh Vishwakarma
**Status:** Feasibility phase (target: ~3–4 weeks)
**Decision gate:** GO / NO-GO into RTL + FPGA prototype + paper

---

## 0. How to use this document

This is a study plan, not the study. Each section has: (a) the question being answered, (b) the concrete work to do, (c) the artifact that section must produce, and (d) the kill-criterion — the result that would tell you to stop or pivot. Treat the kill-criteria as the whole point. The fastest way to win is to find the cheapest experiment that could kill the idea, and run that first.

The single most important output of the entire feasibility study is **one number with error bars**: energy-per-EKF-update (and per inference kernel) for your proposed core versus the best off-the-shelf alternative on the *same* workload. Everything else supports or contextualizes that number.

---

## Section 0.5 — Study Track (read before you build)

**Question:** What do you need to *understand* before each section's work makes sense?

This section is the reading list, keyed to the sections that consume it. The "Reference set" at the bottom of this document lists the competitive/related-work papers you cite *in the paper*; this section lists the docs and background you read *to do the work*. Don't try to read it all up front — pull the rows for the section you're about to start. Links verified June 2026.

**Foundations — read before §1 (the entry point):**
- **PX4 EKF2 / ECL EKF — the workload itself.** Start with the navigation-filter guide, then read the actual covariance code to see the real op structure and confirm the state-vector size (it's **24-state** in current PX4, error-state 23 — quaternion has 4 params / 3 DoF; single-precision float; Joseph-stabilized covariance update).
  - Guide: https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf
  - Source (legacy standalone ECL, clearest to read): https://github.com/PX4/PX4-ECL/blob/master/EKF/covariance.cpp — note ECL is now merged into PX4-Autopilot under `src/modules/ekf2`.
- **Roofline model — the lens for §1 arithmetic-intensity and all of §2.** Read this before you record "ops per byte," because it's *why* that column matters (memory-bound kernels won't benefit from SIMD no matter how wide).
  - Paper (Williams, Waterman, Patterson, CACM 2009): https://dl.acm.org/doi/abs/10.1145/1498765.1498785
  - Free PDF: https://people.eecs.berkeley.edu/~kubitron/cs252/handouts/papers/RooflineVyNoYellow.pdf

**§3 Baselines — the things you're actually competing against:**
- ARM Helium (M-profile Vector Extension / MVE), your *primary* baseline. Concrete optimization examples + concepts: https://github.com/Arm-Examples/Helium-Optimization
- CMSIS-DSP (EKF/matrix/float kernels): https://github.com/ARM-software/CMSIS-DSP
- CMSIS-NN (quantized inference kernels; has scalar / DSP / MVE variants — directly relevant to the int8/int4 tier): https://github.com/ARM-software/CMSIS-NN — docs: https://arm-software.github.io/CMSIS-NN/latest/

**§4 ISA — the RISC-V comparison you must be honest about:**
- RISC-V Vector Extension (RVV v1.0) spec: https://github.com/riscv/riscv-v-spec
- XpulpNN (the "custom packed-SIMD done right" template — 4b/2b types, MAC-and-load, ~6–8× over 8-bit SIMD baseline): https://ieeexplore.ieee.org/document/9406333/ — and its predecessor PULP-NN for the kernel methodology: https://arxiv.org/pdf/1908.11263

**§6 gem5 — extending your existing model:**
- gem5 official docs: https://www.gem5.org/documentation/
- Adding instructions (gem5 bootcamp, most current): https://gem5bootcamp.github.io/gem5-bootcamp-env/modules/developing%20gem5%20models/instructions/
- gem5 v20.0+ paper (arXiv:2007.03152): https://arxiv.org/pdf/2007.03152

**§6–§7 FPGA-feasibility anchors — read the open vector coprocessors that closed timing on real FPGAs:**
- Arrow (RVV-subset ML accelerator, arXiv:2107.07169): https://arxiv.org/abs/2107.07169
- AVA (Southampton CV32E40P RVV coprocessor, Cyclone V @ 50 MHz — your closest FPGA anchor): https://github.com/AI-Vector-Accelerator/ava-core
- Ara ("New Ara," open RVV vector unit, arXiv:2210.08882): https://arxiv.org/abs/2210.08882

**Artifact:** none of its own — this section feeds the others. Treat a row as "done" when you can write that section's workload/baseline/ISA numbers without re-reading.

---

## Section 1 — Workload Characterization (do this first)

**Question:** What exactly are you offloading, and how much of it is there?

This section is non-negotiably first because every downstream decision (ISA, datapath width, memory, interconnect) is determined by the workload. Designing the ISA before profiling is the classic way to waste a month.

**Work to do:**
- Profile the real cycle distribution on Vayu / a PX4 reference. You already know EKF dominates — quantify it. Get a flat profile (per-function cycle %) and identify the top 3–5 kernels.
- Decompose the EKF into primitive ops: matrix multiply (sizes?), matrix inverse / Cholesky, vector add/scale, transpose. Record matrix dimensions and update rates. PX4 EKF2 covariance is 24-state in current versions, not 9 — confirm the actual state vector you're targeting, because that changes the matrix sizes by an order of magnitude in op-count.
- Characterize the mid-tier (keypoint matching, image ops) and light-tier (scaled YOLO) kernels separately. They have very different arithmetic intensity and data types (EKF wants float; inference wants int8/int4).
- For each kernel record: op count per invocation, invocation rate (Hz), working-set size (bytes), data type, and arithmetic intensity (ops per byte). Arithmetic intensity tells you whether you're compute-bound or memory-bound — and a memory-bound kernel will *not* benefit from SIMD no matter how wide you make it. This is the single most common reason vector extensions disappoint (RVV GEMM studies show vectorization can slow memory-bound shapes down).

**Artifact:** A workload table — one row per kernel — with op-count, rate, working set, dtype, arithmetic intensity, and current cycle cost. This is your spec sheet for everything else.

**Kill-criterion:** If, after profiling, the offloadable kernels are mostly memory-bound, or the total offloadable compute is a small fraction of the flight-loop budget, then a SIMD coprocessor buys little and you should stop here. (Cheap to check, kills the project early — that's why it's first.)

---

## Section 2 — Roofline & First-Order Headroom Model

**Question:** Before building anything, what's the theoretical ceiling on the win?

**Work to do:**
- Build a simple roofline for your proposed core: peak ops/sec (lanes × clock × ops/lane) on one axis, achievable memory bandwidth on the other. Plot each kernel from Section 1 on it.
- Estimate, analytically, the speedup ceiling for each kernel at 2/4/8-wide SIMD. Amdahl applies twice: once across kernels (only the offloadable fraction speeds up) and once within each kernel (only the vectorizable part).
- Sanity-check the interconnect. You sketched ~80–120 MB/s for EKF state and ~100–200 MB/s link headroom. Redo this with the *real* covariance size from Section 1, because a 24-state EKF moves far more than a 9-state one (covariance grows as n²).

**Artifact:** A roofline plot + a table of theoretical max speedup per kernel. A one-paragraph statement: "Even in the best case, this design can deliver at most X× on the EKF and Y× on inference, reclaiming Z% of the flight-loop budget."

**Kill-criterion:** If the *theoretical* ceiling (perfect SIMD, no overhead) doesn't clear a meaningful margin over a Cortex-M55 with Helium (which you get for free, off the shelf), then a custom core can't win in practice. Stop or pivot to "just use M55 + CMSIS-DSP."

---

## Section 3 — Competitive Landscape & Baseline Selection

**Question:** What are you actually competing against, and which baselines go in the paper?

This is where you avoid the trap of comparing against a strawman. Pick baselines that are genuinely available to you for the drone use case.

**Work to do — survey these and extract (perf, power, area/cost, toolchain maturity):**

*Off-the-shelf MCU-class with SIMD/DSP (the real competition):*
- ARM Cortex-M55 + Helium (MVE) + optional Ethos-U55/U65 NPU — this is your *primary* baseline. It's the thing a sane engineer would reach for instead of your core.
- ARM Cortex-M7 / M4 with DSP extensions + CMSIS-DSP / CMSIS-NN.
- ESP32-S3 (has a small SIMD extension; cheap; relevant lower bound).

*RISC-V vector / custom-ISA (the academic comparison):*
- PULP platform (RI5CY/CV32E40P, XpulpNN packed-SIMD extension — the XpulpNN paper is directly relevant: 4-bit/2-bit packed SIMD, sum-of-dot-product, ~1.6× over standard MAC).
- Ara / RVV vector coprocessors (Arrow paper, AVA from Southampton — RVV subset, FPGA at 50 MHz, directly comparable to your intended rollout).
- Coral NPU (open RISC-V + custom SIMD for ML dataplane).

*Heavier reference points (context, not direct competitors):*
- Esperanto ET-SoC-1 (datacenter, but the per-core Minion+vector design philosophy is instructive).
- EdgeCortix SAKURA, Jetson-class (to show what you're explicitly *not* trying to be).

**Artifact:** The comparison matrix — rows = candidates, columns = perf on your kernels, power, area/unit-cost, toolchain maturity, FPGA-feasible (Y/N), licensing. Two of those baselines get fully modeled in Section 6.

**Kill-criterion:** If one of the off-the-shelf options already dominates your kernels on perf-and-power-and-cost simultaneously, you have no story. The realistic survivor scenario is that you win on *one axis* (likely energy/op or area for a stripped ISA) — identify which axis before proceeding.

---

## Section 4 — ISA Design Exploration

**Question:** What does the AVR-derived ISA actually look like, and is "derived from AVR" a real advantage or just sunk-cost attachment?

Be ruthlessly honest in this section. The hardest question for the whole project is *why AVR and not RISC-V*. RISC-V is the obvious base for custom vector extensions — it's modular, has a ratified vector spec (RVV), and a mature toolchain. AVR's advantages are simplicity, your existing gem5 model, and your toolchain familiarity. Those are real but they are *engineering-convenience* advantages, not *architectural* advantages. Write down the honest answer before you fall in love with the design.

**Work to do:**
- Define the base subset: which AVR instructions stay (control flow, scalar glue) and which get cut (anything irrelevant to the offload role — a coprocessor doesn't need the full GP ISA).
- Design the SIMD additions: lane width, element types (fp16/fp32 for EKF, int8/int4 for inference — note the data-type split from Section 1 may force you to support both), the key fused ops (MAC, dot-product, sum-of-dot-product à la XpulpNN, maybe a fused multiply-add-accumulate for matrix inner loops).
- Encoding: AVR's 16-bit instruction word is *tight*. Adding vector ops with register/lane/type fields may force 32-bit encodings or a mode bit — document the encoding pressure honestly, because it's a real cost of starting from AVR rather than RISC-V.
- Register file: AVR's 32×8-bit file is too small for vectors. You'll need a separate vector register file — design its width and depth from the working sets in Section 1.

**Artifact:** A draft ISA spec (informal is fine) — instruction list, encodings, register model — plus a one-page honest memo: "Why AVR-derived beats a clean RISC-V + custom extension, *or* an admission that it doesn't and the real reason is tooling/time."

**Kill-criterion:** If the honest memo concludes that every AVR advantage is convenience rather than architecture, seriously consider re-basing on RV32 + a custom extension. That's not a failure — it's the feasibility study doing its job. (You can still reuse most of the gem5 and benchmarking work.)

---

## Section 5 — Toolchain Feasibility

**Question:** Can you actually generate code for this thing without building a compiler from scratch?

This kills more custom-ISA projects than the hardware does. A novel ISA with no compiler is a research dead-end.

**Work to do:**
- Assess the avr-gcc fork path realistically. Adding SIMD intrinsics / new instruction patterns to GCC's AVR backend is substantial work, and avr-gcc is not the friendliest backend. Scope it.
- Compare against alternatives: (a) LLVM backend (cleaner for custom extensions than GCC), (b) intrinsics-only + hand-written assembly for the hot kernels (pragmatic for a feasibility prototype — you only have ~5 kernels), (c) an ASIP toolflow (Synopsys ASIP Designer / nML auto-generates a C compiler + ISS from an architecture description — this is the industry-standard shortcut and worth evaluating even if you don't buy it, because it tells you what "good" looks like).
- Decide the minimum viable toolchain for the feasibility study specifically. You do *not* need a production compiler to publish — you need to compile ~5 benchmark kernels. Intrinsics + assembly for those kernels is almost certainly the right call for the feasibility phase.

**Artifact:** A toolchain decision memo + a scoping estimate (person-weeks) for the production compiler path, separated from the feasibility-phase path.

**Kill-criterion:** If even the feasibility-phase path (hand-coding 5 kernels) requires a compiler effort that dwarfs the hardware work, the ISA is too ambitious — simplify it.

---

## Section 6 — gem5 Modeling & Benchmarking (the core experiment)

**Question:** On a cycle-accurate model, does the proposed core beat the baselines on your kernels?

This is where your existing gem5 AVR work pays off. You've already validated functional and cycle accuracy against real ATmega328P and against simulation — that credibility is your foundation. Now extend it.

**Work to do:**
- Add the SIMD ISA to your gem5 AVR model (instruction definitions, the vector register file, a timing model for the vector datapath). Reuse your existing validation harness.
- Model the coprocessor + host link with realistic latency/bandwidth from Section 2.
- Implement the Section 1 kernels (EKF predict/update, one mid-tier kernel, one light inference kernel) on your model.
- Run the *same* kernels on gem5 models of the two chosen baselines from Section 3. gem5 has mature ARM support (NEON, and you can approximate M-class); RISC-V vector models exist. Where a faithful model doesn't exist, fall back to published numbers from the baseline's own papers and clearly label it as such.
- Collect: cycles, estimated energy (cycle counts × per-op energy estimates — be explicit that gem5 gives you timing, not power; energy needs an activity-based estimate or a McPAT-style model, and you must state the uncertainty).

**Artifact:** The benchmark results table — your core vs. 2 baselines, per kernel: cycles, latency-vs-deadline, estimated energy/op, with error bars and a clear statement of what's measured vs. modeled vs. cited.

**Kill-criterion:** If on a cycle-accurate model you don't beat the best off-the-shelf baseline on at least one axis by a margin larger than your modeling uncertainty, there's no defensible result. This is the real GO/NO-GO gate.

---

## Section 7 — Area, Power & FPGA-Rollout Reality Check

**Question:** Will this fit and close timing on the FPGA you'd actually use, and does the energy story survive contact with FPGA overheads?

**Work to do:**
- Estimate LUT/DSP/BRAM for the vector datapath at your chosen width (back-of-envelope from comparable open cores — Ara, CV32E40P, the AVA RVV coprocessor closed timing on a Cyclone V at 50 MHz; that's a useful anchor).
- Identify a concrete target FPGA and check resource fit + plausible clock.
- Be explicit that FPGA power/area will *not* match an ASIC — for a research artifact and proof-of-concept that's fine, but the paper's energy claims must distinguish "FPGA-measured" from "ASIC-projected." Conflating them is the fastest way to get a paper rejected.

**Artifact:** Resource-and-timing estimate + a named target board + an honest "what FPGA proves vs. what it doesn't" paragraph.

**Kill-criterion:** If it can't fit or can't hit a clock where it beats the baseline, the FPGA story collapses and the project becomes "ASIC-only," which is far beyond feasibility-phase scope.

---

## Section 8 — Synthesis, Decision, and Paper Framing

**Question:** GO or NO-GO, and if GO, what's the paper's actual contribution claim?

**Work to do:**
- Consolidate Sections 1–7 into a single GO/NO-GO recommendation against the kill-criteria.
- If GO: write the one-sentence contribution claim. Realistically it will *not* be "cheaper than off-the-shelf" (Section 3 will likely show it isn't). It will be something like: "an open, minimal, AVR-derived SIMD ISA that achieves [X]× energy efficiency on EKF-class flight-control workloads versus [baseline] at comparable area, with an open toolchain and FPGA implementation." Identify the defensible axis from your own data — don't pre-commit to it.
- Identify the venue (embedded systems / FPGA / computer-architecture workshops are more receptive to "novel ISA + FPGA proto" than top-tier arch conferences that will demand silicon).

**Artifact:** A 1-page decision memo + a paper abstract draft built only from results you actually have.

---

## Suggested sequencing (≈3–4 weeks)

| Phase | Sections | Why this order |
|---|---|---|
| Week 1 | §1 Workload, §2 Roofline | Cheapest kills first. If the workload or roofline says no, you've spent days, not weeks. |
| Week 1–2 | §3 Landscape, §4 ISA | Pick baselines and draft the ISA against real numbers. |
| Week 2 | §5 Toolchain | Decide the minimum path before building anything. |
| Week 2–3 | §6 gem5 + benchmarks | The core experiment. Most of your time. |
| Week 3–4 | §7 FPGA check, §8 Decision | Reality-check and write the GO/NO-GO. |

---

## Reference set (starting points — extend these yourself)

**Closest-to-your-use-case papers (read first):**
- *Arrow: A RISC-V Vector Accelerator for ML Inference* — arXiv:2107.07169. RVV-subset coprocessor for edge ML; directly parallels your design choices.
- *FPGA design of EKF block accelerator for 3D visual SLAM* (Computers & Electrical Engineering) — systolic EKF coprocessor; the EKF-specific hardware reference. Related: *FPGA matrix-multiplier accelerator for 3D EKF SLAM* (≈7.3× over software).
- XpulpNN (PULP) — packed-SIMD ISA extension for QNN inference on MCU-class cores; the template for "custom SIMD ISA extension done right."

**Custom-ISA / ASIP methodology:**
- *An ASIP for Neural Network Inference on Embedded Devices with 99% PE Utilization* (PMC) — SIMD ASIP design methodology, area/power framing.
- Synopsys ASIP Designer / nML documentation — industry-standard ASIP design + auto-generated compiler+ISS; read for methodology even if you don't license it.

**Vector / RISC-V baselines:**
- RISC-V Vector Extension (RVV) v1.0 spec.
- Ara (PULP) and AVA (Southampton CV32E40P RVV coprocessor, FPGA at 50 MHz) — your FPGA-feasibility anchors.
- Coral NPU (Google) — open RISC-V + custom SIMD for ML.

**Off-the-shelf baselines (datasheets/white papers):**
- ARM Cortex-M55 + Helium (MVE), Ethos-U55/U65, CMSIS-NN/CMSIS-DSP.
- ESP32-S3 SIMD extension (esp-dsp).

**Platform / tooling:**
- gem5 ISA-extension docs + *The gem5 Simulator: Version 20.0+* (arXiv:2007.03152).
- PX4 EKF2 docs + `src/modules/ekf2` source — for real workload characterization (confirm the actual state-vector size).

**Historical caution:**
- AVR32 (Wikipedia + Atmel docs) — had FPU + SIMD/DSP, now dead (dropped from Linux, GCC support never mainlined). Worth one paragraph in your related-work: a SIMD AVR-family architecture already existed and didn't survive. Know *why* before you repeat it.
