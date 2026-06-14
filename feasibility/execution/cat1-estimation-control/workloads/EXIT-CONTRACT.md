# Cat-1 Harness Exit Contract

Defines **once** what counts as a *valid exit* (a usable measurement) for every Cat-1 workload
run on the gem5 AVR model. Each workload's `EXIT-CRITERIA.md` adds only its workload-specific
input, golden reference, tolerance, and invocation counts.

## Workloads

| Dir | Plan | Kernel under test |
|---|---|---|
| `11-ekf` | 1.1 | EKF covariance predict (`predictCovariance`, 24-state) |
| `12-ahrs` | 1.2 | Attitude estimation (Madgwick / Mahony update step) |
| `13-quaternion` | 1.3 | Quaternion / rotation kernels (mul, normalize, rotate, DCM) |
| `14-control-pid` | 1.4 | Cascaded PID / rate / attitude control step |
| `15-control-allocation` | 1.5 | Control allocation (pseudo-inverse mix) |

## Run model

Each workload is a self-contained AVR ELF (built with `avr-gcc` on **A**, run on
`build/AVR/gem5.opt` on **B** via a per-workload gem5 SE config in that workload's `harness/`). Flow:

1. **Init** a fixed, deterministic input — no RNG, no clock reads, no I/O.
2. **Run** the kernel `N` times in a loop (`N` per workload).
3. **Self-validate** the output against an embedded golden reference (computed off-line by the
   *same* kernel built natively on the host).
4. **Exit** through the SE-mode exit syscall (`test_syscall.S` shim) with status `0` (pass) / `1` (fail).

## Valid exit — ALL must hold (else the run is discarded)

1. **Clean termination** — gem5 stops with cause **`AVR Syscall Exit`**. NOT `fatal`, NOT an
   unimplemented/illegal instruction, NOT panic, NOT max-tick / timeout.
2. **Functional correctness** — self-check passes ⇒ program **exit status 0** (output within the
   workload's tolerance of golden). A correct op-mix can only be claimed from a correct run.
3. **Measurable** — `stats.txt` written; `simInsts > 0`; the **op-class histogram** is present.
4. **Deterministic** — same ELF + input ⇒ identical `simInsts` on repeat.

## Op-mix isolation — two-run difference

The AVR model has no `m5` magic-op region markers, so isolate the kernel's *per-invocation* op-mix
by differencing two otherwise-identical runs that differ only in loop count:

```
per_invocation(op) = ( stats_N2(op) − stats_N1(op) ) / (N2 − N1)
```

This cancels fixed startup/teardown and the validation code. **Both** runs must independently be
valid exits. (If the model later gains `m5_reset_stats`/`m5_dump_stats`, use those instead.)

## Validation oracle — deterministic, reproducible end goal

gem5's AVR port is new, so an op-mix is trusted only after the run is proven correct against a
**deterministic, reproducible oracle**. The primary oracle works for **every** kernel regardless of
size (so the >2 KB EKF is *not* a gap); hardware is an extra silicon check where the kernel fits.

### Tier 1 (always) — host reference + matched intermediate traces

Build the **same kernel source** two ways: a **host reference** (native x86-64, SSE fp32, built
`-ffp-contract=off -fno-fast-math` ⇒ IEEE-754 round-nearest-even single) and the **gem5 AVR** build
(avr-gcc softfloat, same IEEE-754 single). Both emit a **trace**: a sequence of intermediate checkpoint
values at fixed points in the kernel — *not only the final output* — as raw IEEE-754 hex.
**Validity = the gem5 trace matches the host trace checkpoint-by-checkpoint**; the first divergence
pinpoints the gem5 ISA bug.

- **Deterministic / reproducible:** fixed input, zero-init state, no RNG/clock; pinned toolchain+flags;
  the reference trace + ELF + inputs are committed → the identical trace reproduces forever.
- **Bit-exact where it counts:** for the IEEE-754-mandated ops `+ − × ÷ √`, host-SSE and AVR-libgcc
  softfloat are both correctly-rounded RNE single ⇒ traces match **bit-for-bit** (compare 32-bit hex).
  Non-mandated transcendentals (`sinf`/`cosf`/`expf`, fast-invsqrt) are not bit-portable → vendor one
  **shared implementation** (same code both sides) or compare those checkpoints within the workload
  tolerance — documented per workload.
- **Non-intrusive tracing:** trace emission is **read-only snapshots guarded by `#ifdef TRACE`** — it
  never alters the kernel's data or control flow. Validate with `TRACE` **on** (host↔gem5 match), then
  **measure the op-mix with `TRACE` off** (clean histogram). Same kernel ⇒ the measured run inherits the
  validated run's correctness.
- Each workload's `EXIT-CRITERIA.md` defines its **checkpoints** (which intermediates, how many).

### Tier 2 (where it fits 2 KB SRAM) — real ATmega328P

Additionally run on the **Nano** (`/dev/ttyUSB1`, ATmega328P sig `0x1e950f`, flash
`avrdude -c arduino -b 115200`; second CH340 on `ttyUSB0` left alone) and confirm the same trace/output
— silicon ground truth that also validates the host reference. Bonus: Nano `TCNT1` cycles vs gem5
`numCycles` checks the per-instruction cycle model. Kernels that don't fit (full 24-state EKF, ~4.6 KB)
are fully validated by Tier 1 alone.

Any **mismatch** (Tier 1 or 2) is bisected to the first diverging checkpoint/op = a gem5 AVR ISA bug →
fix in `src/arch/avr`, rebuild, re-run (same finding loop as an unimplemented-opcode fatal).

## Recorded on a valid exit

- op-class histogram (the "what they use most")
- `simInsts`, `numCycles`, CPI
- per-invocation op deltas (from the two-run difference)
- working-set bytes and dtype (from source/build)

## Invalid exit — handling

Any failing condition ⇒ **discard** the run and **log the cause**. The gem5 AVR port now **hard-halts
(panics) on any unimplemented/undecoded opcode** — it no longer silently skips — printing
`AVR: unimplemented/undecoded instruction opcode=0x........ at PC=0x........`. That panic is itself a
finding: it names the exact **AVR ISA gap** to implement in `src/arch/avr` before the workload can be
characterized. Track such gaps in the workload's `harness/`. (Implemented 2026-06-14 in
`faults.cc` + `types.hh` + `isa/templates/templates.isa`.)
