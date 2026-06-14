# AVR-XPU

**AVR-XPU** — an **eXtensible** AVR-derived SIMD coprocessor for edge inference and flight-control
offload (EKF / DSP / lightweight NN), explored as a feasibility study and validated in gem5 with a
deterministic host-reference + (where it fits) real-hardware ground-truth loop.

This repository holds the **feasibility study** and its **workload-characterization harness**. The gem5
AVR model and the eXtended ISA live in a separate gem5 fork
([ragnar-vallhala/gem5](https://github.com/ragnar-vallhala/gem5), branch `btp`).

## Layout

- `feasibility/plan.md` — the 8-section feasibility plan (workload → roofline → baselines → ISA →
  toolchain → gem5 modeling → FPGA → GO/NO-GO).
- `feasibility/execution/` — the workload-characterization harness:
  - `test-plan.md` — what we measure and how: **A** static op-count, **B** gem5 instruction-mix,
    **C** literature, **D** deterministic host+trace validation (with hardware where it fits).
  - `cat1-estimation-control/`, `cat2-dsp/`, `cat3-inference/` — per-category kernel sources
    (each `SOURCES.md` records provenance + license) and, for Cat 1, per-workload harnesses
    (`workloads/<id>/`) with `EXIT-CRITERIA.md` under a shared `EXIT-CONTRACT.md`.

## Validation approach

Every gem5 run is proven against a **deterministic, reproducible oracle**: the *same* kernel source is
built for the host and for AVR and both emit matched intermediate **traces** (bit-exact for the
IEEE-754-mandated ops `+ − × ÷ √`). Where a kernel fits a real ATmega328P's 2 KB SRAM it is also checked
on silicon. The gem5 AVR port **hard-halts on any unimplemented opcode**, so ISA gaps surface
immediately and get implemented — the "eXtensible" in AVR-XPU.

First validated workload: a 24-state EKF covariance predict, gem5 output bit-identical to the host
reference across all checkpoints.

## Notes

- Third-party study PDFs are **not** committed (copyright); the docs reference them by URL.
- Collected kernel sources are upstream open-source (CMSIS Apache-2.0, PX4 BSD-3, Madgwick/Mahony /
  Fusion) — retained with their headers; see each `SOURCES.md` for attribution.
