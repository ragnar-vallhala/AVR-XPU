# Workload Test Plan — "What They Use Most"

Execution plan for **§1 Workload Characterization** (and the inputs it feeds: §2 Roofline, §3 Baselines, §4 ISA) in [`../plan.md`](../plan.md).

**Goal of this phase:** for a representative *set* of edge flight-control / DSP / inference kernels,
quantify **which operations dominate** ("what they use most"), in what data type, over what
working set — so the SIMD ISA is designed against real op-mix evidence, not intuition.

**The one number this feeds:** arithmetic intensity (FLOP/byte) per kernel → the roofline →
the speedup ceiling. A kernel that is memory-bound will *not* benefit from SIMD; finding those
early is the cheapest kill-criterion.

---

## Scope: three categories (status — *proposed, confirm before building*)

### Category 1 — Estimation & Control  (fp32; the flight-control core)
Broadened beyond sensor fusion to a **set** of the algorithms a flight controller actually runs,
so the ISA isn't over-fit to the EKF alone.

| # | Kernel | Role | Source | Status |
|---|---|---|---|---|
| 1.1 | **EKF covariance predict + update** (PX4 ECL EKF2, 24-state) | sensor fusion | `../study-material/01-foundations/px4-ecl-covariance.cpp` | have source ✓ |
| 1.2 | **Madgwick / Mahony AHRS** | attitude estimation (lightweight fusion) | reference impl (to add) | to source |
| 1.3 | **Quaternion / rotation kernels** (q-mul, normalize, rotate-vec, DCM) | the glue used by everything above | reference impl (to add) | to source |
| 1.4 | **Cascaded PID** (rate→attitude→position, w/ FF + anti-windup) | control | PX4 / reference impl | to source |
| 1.5 | **Control allocation / mixer** (effectiveness matrix × setpoint, ± pseudo-inverse) | control | PX4 / reference impl | to source |
| 1.6 | *(bridge)* **Biquad IIR notch/LP** on gyro | pre-filter | CMSIS / reference | optional |

### Category 2 — DSP / mid-tier  (fp32 / fp16 / q15)
The signal-processing primitives, and the linear-algebra that EKF-update and MPC also lean on.

| # | Kernel | Role | Source |
|---|---|---|---|
| 2.1 | **FIR filter** (`arm_fir_f32`) | filtering | CMSIS-DSP reference C |
| 2.2 | **Biquad IIR cascade** (`arm_biquad_cascade_df1_f32`) | filtering | CMSIS-DSP |
| 2.3 | **FFT** (radix-2 / `arm_rfft`) | spectral (gyro notch tuning) | CMSIS-DSP |
| 2.4 | **Matrix mult + Cholesky / inverse** | linear algebra (EKF update, MPC) | CMSIS-DSP |
| 2.5 | **Vector kernels** (dot, axpy, norm) | building blocks | CMSIS-DSP |

### Category 3 — Light inference  (int8 / int4)
The quantized-NN tier; the data-type split from Cat 1/2 (float→int) is the central ISA tension.

| # | Kernel | Role | Source |
|---|---|---|---|
| 3.1 | **Conv2D s8** (`arm_convolve_s8`) + depthwise | conv backbone | CMSIS-NN reference C |
| 3.2 | **Fully-connected / GEMM s8** (`arm_fully_connected_s8`) | classifier head | CMSIS-NN |
| 3.3 | **Pool + activation + requantize** | glue | CMSIS-NN |
| 3.4 | *(light tier)* tiny detector block (scaled-YOLO-style int8 conv stack) | object detection | from 3.1/3.2 |

---

## What we measure (per kernel — the workload-table columns)

1. **Dominant op(s)** — the headline "what they use most" (e.g. fp32 MAC, int8 sum-of-dot-product).
2. **Static op count per invocation** — mul, add/MAC, div, transcendental (sin/cos/sqrt/exp), load, store, branch.
3. **Data type** — fp32 / fp16 / q15 / int8 / int4.
4. **Working-set size (bytes)** — inputs + state + outputs (vs. ATmega 2 KB SRAM as a reference point).
5. **Arithmetic intensity (FLOP/byte)** — drives the roofline; the compute- vs memory-bound verdict.
6. **Invocation rate (Hz)** — from the flight-loop budget (*proposed defaults below, confirm*).
7. **Measured AVR cost** — cycles / CPI from the gem5 AVR model (empirical kernels only).
8. **Verdict** — compute-bound vs memory-bound; SIMD-amenable Y/N and at what width.

Proposed flight-loop rates (confirm): rate-control loop ~1 kHz, attitude ~250 Hz, position ~50 Hz,
EKF predict ~ IMU rate (250–1000 Hz), inference ~10–30 Hz. These set the per-second op budget.

---

## Method — three levels (which applies to which kernel)

| Level | What | Applied to |
|---|---|---|
| **A. Static op-count** | parse the C/C++ source, count ops per kernel (script in `harness/`) | every kernel with source (EKF now; CMSIS refs once pulled) |
| **B. Empirical instruction-mix** *(gold standard)* | cross-compile kernel with `avr-gcc` (on A) → AVR ELF → run on `build/AVR/gem5.opt` (on B) → read gem5 **op-class histogram** + cycles | a representative kernel from each category (≥ 1.1, 2.1/2.4, 3.1) |
| **C. Literature** | cite baseline papers for ops we don't compile + to cross-check | Helium / CMSIS / XpulpNN / PULP-NN rows |
| **D. Deterministic cross-validation** | host-reference run + **matched intermediate traces** (works for *all* kernels, any size) is the reproducible oracle that proves a gem5 run; real ATmega328P (Nano) is an extra silicon check where it fits in 2 KB SRAM. **B is trusted only once D agrees.** | every kernel (Tier 1); + Nano (Tier 2) where it fits |

Toolchain reality (confirmed): `avr-gcc 7.3.0` on A; the CoreMark build pattern
(C/asm + `test_syscall.S` SE-mode shim + `Makefile`) is the template for new kernels.
`avr-gcc` is **not** on B → **build ELFs on A, run on B**.

### Level D — Deterministic cross-validation (proves the gem5 run)

The gem5 AVR port is **new**, so a Level-B op-mix is trusted only after the run is proven correct
against a **deterministic, reproducible oracle**. The primary mechanism works for *every* kernel
regardless of size; real hardware is an extra silicon check where the kernel fits.

#### D1 (always) — host reference + matched intermediate traces

Build the **same kernel source** two ways — **host reference** (native x86-64, SSE fp32,
`-ffp-contract=off -fno-fast-math` ⇒ IEEE-754 round-nearest-even single) and **gem5 AVR** (avr-gcc
softfloat, same IEEE-754 single). Both emit a **trace**: intermediate checkpoint values at fixed points
in the kernel — *not only the final output* — as raw IEEE-754 hex. **Validity = the gem5 trace matches
the host trace checkpoint-by-checkpoint**; the first divergence pinpoints the gem5 ISA bug.

- **Deterministic / reproducible** — fixed input, zero-init state, no RNG/clock; pinned toolchain+flags;
  committed reference trace + ELF + inputs ⇒ the same trace reproduces forever.
- **Bit-exact where it counts** — for IEEE-754-mandated ops `+ − × ÷ √`, host-SSE and AVR-libgcc
  softfloat are both correctly-rounded RNE single ⇒ traces match **bit-for-bit** (32-bit hex compare).
  Non-mandated transcendentals (`sinf`/`cosf`/`expf`, fast-invsqrt) → vendor one shared implementation
  or compare those checkpoints within tolerance (per workload).
- **Non-intrusive tracing** — trace emission is **read-only snapshots guarded by `#ifdef TRACE`**; it
  never changes the kernel's data or control flow. Validate with `TRACE` **on** (host↔gem5 match), then
  **measure the op-mix with `TRACE` off** (clean histogram). Same kernel ⇒ measured run inherits the
  validated run's correctness.

#### D2 (where it fits 2 KB SRAM) — real ATmega328P

Additionally run on the **Nano** (`/dev/ttyUSB1`, ATmega328P sig `0x1e950f`, flash with `avrdude 7.1`
`-c arduino -b 115200`; 57600 fails → new bootloader; `arduino-cli` also present; user in `dialout`;
second CH340 on `ttyUSB0` left alone). Same source, thin UART-print harness; confirm the same
trace/output — silicon ground truth that also validates the host reference. Bonus: Nano `TCNT1` cycles
vs gem5 `numCycles` validates the per-instruction cycle model.

**The full 24-state EKF (~4.6 KB) does not fit the 328P's 2 KB SRAM — but this is no longer a validation
gap:** D1 (host + trace match) is a complete deterministic check on its own; hardware simply can't
exercise it. (Run a reduced-state EKF on the Nano if a silicon datapoint is still wanted, or use a 6 KB
AVR — open question #6.) Any mismatch (D1 or D2) → bisect to the first diverging checkpoint → fix in
`src/arch/avr`, rebuild, re-run. *This is the loop that fixes the AVR sim along the way.*

---

## Harness (built in `harness/`, only after this plan is signed off)

- `count_ops.py` — static op counter (Level A) emitting a per-kernel op table.
- `build_kernel.sh` — avr-gcc + syscall-shim → ELF (Level B build, on A).
- `run_isa_mix.sh` — run ELF on `build/AVR/gem5.opt` (B), extract op-class histogram + cycles.
- one gem5 SE config per kernel (modeled on `run_coremark.py`).

## Deliverables

1. `feasibility/workload-analysis.md` — the consolidated workload table (the §1 artifact).
2. Per-category raw data under `cat{1,2,3}-*/` (op counts, gem5 stats).
3. Roofline inputs for §2 (arithmetic intensity per kernel).

---

## Open scope questions (resolve before building)

1. **Cat 1 algorithm set** — confirm/add/cut 1.2–1.6. Anything specific to *your* target airframe
   (e.g. MPC, allocation method, a particular AHRS)?
2. **Target platform reference** — ATmega-class (8-bit, 2 KB SRAM) only, or also a larger AVR
   (more SRAM) as the realistic coprocessor host? This changes the memory-bound verdicts.
3. **Inference target** — is scaled-YOLO the real light-tier workload, or a classifier/keypoint net?
4. **Rates** — confirm the flight-loop rates above.
5. **avr-gcc fp** — 8-bit AVR has no FP hardware; fp32 is softfloat library calls. Decide whether
   Level-B fp kernels measure softfloat AVR (honest baseline) or we model fp at the op level.
6. **HiL board** — is the Nano (ATmega328P, 2 KB SRAM) the only board for the Level-D ground-truth
   check, or is a larger AVR available (e.g. Nano Every / ATmega4809, 6 KB SRAM) so the **full
   24-state EKF** can be validated on real hardware instead of only a reduced-state variant?
