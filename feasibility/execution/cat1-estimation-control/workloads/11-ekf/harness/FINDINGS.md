# 11-ekf harness — findings (gem5 AVR ISA gaps)

Per `../EXIT-CONTRACT.md`: gem5 now hard-halts on any unimplemented opcode; each halt is logged here
as an AVR ISA gap to close.

## F1 — ELPM not implemented (2026-06-14)  [RESOLVED 2026-06-14]

**Resolution:** implemented `ELPM Rd,Z` (`0x6`) and `ELPM Rd,Z+` (`0x7`) in
`src/arch/avr/isa/decoder/decoder.isa` (read `RAMPZ:Z` program memory; Z+ form post-increments the
24-bit pointer incl. RAMPZ), and aliased I/O `0x3b` ↔ `MISCREG_RAMPZ` in `in_instr`/`out_instr`.
After rebuild, `ekf_avr_trace.elf` runs to clean `AVR Syscall Exit` and its trace matches the host
reference **bit-for-bit (91/91 checkpoints, CRC 26175af3)** — first fully-validated gem5 EKF run.
(Implied `ELPM r0,Z` = `0x95D8` not yet added; not emitted by avr-gcc here — add if a halt surfaces it.)

### Original report  [was OPEN]

- **Symptom:** `panic: AVR: unimplemented/undecoded instruction opcode=0x00009007 at PC=0xa8`
- **Decode:** `0x9007` = `elpm r0, Z+` (objdump), inside `__do_copy_data` (the C-runtime `.data`
  flash→RAM copy loop).
- **Why hit:** the EKF working set (24×24 fp32 ≈ 4.6 KB) forces a ≥8 KB-SRAM AVR; all such parts have
  >64 KB flash, so avr-gcc's crt uses **ELPM** (with RAMPZ) instead of LPM to copy initialized `.data`.
  We target `atmega1284p`. So the gap is hit at **startup**, before the kernel runs.
- **Scope:** ELPM family — `ELPM Rd,Z` (`1001 000d dddd 0110`), `ELPM Rd,Z+` (`...0111`), and the
  implied-R0 `ELPM` (`0x95D8`); needs the **RAMPZ** I/O register. (Check whether plain LPM is already
  implemented — ELPM is LPM + RAMPZ high byte.)

### Resolution options
- **A (proper):** implement ELPM (+ RAMPZ) in `src/arch/avr` → keeps `atmega1284p`, unblocks any
  large-flash workload. Likely surfaces further gaps (softfloat lib) which we then fix in turn.
- **B (sidestep):** target a ≤64 KB-flash avr5 part (crt uses LPM, no ELPM) — but those cap at 4 KB
  SRAM (`atmega644p`), so also shrink the arrays to 16×16 (≈2 KB, still exercises states 0..15).
  Gets a running gem5 result now; defers ELPM.
