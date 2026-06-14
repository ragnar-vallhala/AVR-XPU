#!/usr/bin/env bash
# Run every cross-ISA binary through gem5, capture roofline stats:
#   wl isa it crc simInsts cycles fpops intmac dbytes
# dbytes = data bytes moved (mem-ctrl, arch-independent); fpops/intmac from
# committed op-class histogram. Per-invocation work = (i11-i1)/10 later.
set -u
cd ~/space/AVR/gem5/wlruns
G=../build/ALL/gem5.opt; SE=../configs/deprecated/example/se.py
WLS="11-ekf 12-ahrs 13-quaternion 14-control-pid 15-control-allocation 21-fir 22-biquad 23-fft 24-matmul 25-dotprod 31-conv2d 32-fc 33-maxpool"
FPC="FloatAdd|FloatMult|FloatMultAcc|FloatDiv|FloatSqrt|SimdFloatAdd|SimdFloatMult|SimdFloatMultAcc|SimdFloatDiv|SimdFloatSqrt|SimdFloatReduceAdd"
INC="::IntMult |::IntMultAcc |SimdMult |SimdMultAcc |SimdMatMultAcc "
: > xroof_results.txt
for wl in $WLS; do
  for isa in arm rv; do
    if [ "$isa" = arm ]; then bin=${wl}_arm64; cpu="ArmAtomicSimpleCPU --arm-iset=aarch64"; else bin=${wl}_rv64; cpu="RiscvAtomicSimpleCPU"; fi
    for it in 1 11; do
      od=/tmp/xr_${wl}_${isa}_${it}
      timeout 600 $G -d $od $SE --cpu-type=$cpu -c ${bin}_i${it} >$od.out 2>$od.err
      st=$od/stats.txt
      crc=$(grep -oE "CRC [0-9a-f]+" $od.out | head -1 | awk "{print \$2}")
      si=$(grep -E "^simInsts " $st | awk "{print \$2}")
      cy=$(grep -E "numCycles " $st | head -1 | awk "{print \$2}")
      fp=$(grep -E "committedInstType::($FPC) " $st | awk "{s+=\$2} END{print s+0}")
      im=$(grep -E "committedInstType::($INC)" $st | awk "{s+=\$2} END{print s+0}")
      rb=$(grep -E "bytesRead::cpu.data " $st | awk "{print \$2}"); rb=${rb:-0}
      wb=$(grep -E "bytesWritten::cpu.data " $st | awk "{print \$2}"); wb=${wb:-0}
      db=$((rb + wb))
      echo "$wl $isa $it ${crc:-NA} ${si:-0} ${cy:-0} ${fp:-0} ${im:-0} $db" | tee -a xroof_results.txt
    done
  done
done
echo "DONE $(wc -l < xroof_results.txt) lines"
