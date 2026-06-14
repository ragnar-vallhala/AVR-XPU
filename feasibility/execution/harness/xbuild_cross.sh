#!/usr/bin/env bash
# Cross-compile every workload for ARM64 + RISC-V (i1 & i11), static, -O1 (to
# match the AVR build), into B's gem5 wlruns dir (via the sshfs mount on A).
# Writes a sentinel /tmp/xbuild.done when finished so it can be monitored.
set -u
EX=~/Documents/avr/feasibility/execution
HG=$EX/harness
W=/tmp/xisa                              # LOCAL output (fast); pushed to B afterward
FL="-O1 -static -s -ffp-contract=off -fno-fast-math"   # -s strips => smaller transfer
mkdir -p $W; rm -f /tmp/xbuild.done; : > /tmp/xbuild.log

# name  dir(relative to $EX)  kernel.c  main-mode(own|wl)  iters-macro
entries=(
"11-ekf cat1-estimation-control/workloads/11-ekf/harness ekf_kernel.c own EKF_ITERS"
"12-ahrs cat1-estimation-control/workloads/12-ahrs/harness ahrs_kernel.c own AHRS_ITERS"
"13-quaternion cat1-estimation-control/workloads/13-quaternion/harness quat_kernel.c own QUAT_ITERS"
"14-control-pid cat1-estimation-control/workloads/14-control-pid/harness pid_kernel.c own PID_ITERS"
"15-control-allocation cat1-estimation-control/workloads/15-control-allocation/harness alloc_kernel.c own ALLOC_ITERS"
"21-fir cat2-dsp/workloads/21-fir/harness fir_kernel.c wl ITERS"
"22-biquad cat2-dsp/workloads/22-biquad/harness biquad_kernel.c wl ITERS"
"23-fft cat2-dsp/workloads/23-fft/harness fft_kernel.c wl ITERS"
"24-matmul cat2-dsp/workloads/24-matmul/harness matmul_kernel.c wl ITERS"
"25-dotprod cat2-dsp/workloads/25-dotprod/harness dotprod_kernel.c wl ITERS"
"31-conv2d cat3-inference/workloads/31-conv2d/harness conv2d_kernel.c wl ITERS"
"32-fc cat3-inference/workloads/32-fc/harness fc_kernel.c wl ITERS"
"33-maxpool cat3-inference/workloads/33-maxpool/harness maxpool_kernel.c wl ITERS")

for e in "${entries[@]}"; do
  set -- $e; name=$1; dir=$EX/$2; kern=$3; mode=$4; macro=$5
  [ "$mode" = wl ] && main="$HG/wl_main.c" || main="$dir/main.c"
  ok=1
  for IT in 1 11; do
    aarch64-linux-gnu-gcc $FL -D$macro=$IT -I$HG -I$dir $main $dir/$kern -o $W/${name}_arm64_i$IT || ok=0
    riscv64-linux-gnu-gcc $FL -D$macro=$IT -I$HG -I$dir $main $dir/$kern -o $W/${name}_rv64_i$IT  || ok=0
  done
  echo "$name: $([ $ok = 1 ] && echo OK || echo FAIL)" | tee -a /tmp/xbuild.log
done
echo "DONE arm64=$(ls $W/*_arm64_i11 2>/dev/null|wc -l)/13  rv64=$(ls $W/*_rv64_i11 2>/dev/null|wc -l)/13" | tee -a /tmp/xbuild.log
touch /tmp/xbuild.done
