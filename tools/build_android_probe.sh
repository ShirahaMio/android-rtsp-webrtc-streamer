#!/usr/bin/env bash
set -euo pipefail
SRC="${WRS_BUILD_ROOT:-/opt/android-build}/webrtc/src"
WORK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$WORK/dist/diagnostics/arm64-v8a"
"$SRC/third_party/llvm-build/Release+Asserts/bin/clang" \
  --target=aarch64-linux-android28 \
  --sysroot="$SRC/third_party/android_toolchain/ndk/toolchains/llvm/prebuilt/linux-x86_64/sysroot" \
  -fuse-ld=lld -unwindlib=none -O2 -mbranch-protection=none -mno-outline-atomics -fPIE -pie -Wl,-z,max-page-size=16384 \
  -Wl,--pack-dyn-relocs=none "$WORK/tests/android_probe.c" -ldl \
  -o "$WORK/dist/diagnostics/arm64-v8a/wrs_probe"
file "$WORK/dist/diagnostics/arm64-v8a/wrs_probe"
