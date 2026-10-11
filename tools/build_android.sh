#!/usr/bin/env bash
set -euo pipefail
ROOT="${WRS_BUILD_ROOT:-/opt/android-build}"
WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/tmp" "$WORKSPACE/logs"
export TMPDIR="$ROOT/tmp"
export XDG_CACHE_HOME="$ROOT/cache"
export VPYTHON_VIRTUALENV_ROOT="$ROOT/cache/vpython"
export CIPD_CACHE_DIR="$ROOT/cache/cipd"
export DEPOT_TOOLS_UPDATE=0
export PATH="/usr/bin:$ROOT/depot_tools:$PATH"
cd "$ROOT/webrtc/src"
python3 "$WORKSPACE/tools/prepare_android_target.py" "$PWD"
mkdir -p out/android-arm64
cat > out/android-arm64/args.gn <<'EOF'
target_os = "android"
target_cpu = "arm64"
android_ndk_api_level = 28
use_relative_vtables_abi = false
arm_control_flow_integrity = "none"
is_debug = false
is_component_build = false
symbol_level = 1
rtc_include_tests = false
rtc_build_examples = false
rtc_enable_protobuf = false
rtc_include_internal_audio_device = false
rtc_use_h264 = false
rtc_use_h265 = true
rtc_use_x11 = false
rtc_use_pipewire = false
use_custom_libcxx = true
treat_warnings_as_errors = false
use_remoteexec = false
use_siso = false
EOF
buildtools/linux64/gn gen out/android-arm64 --root-target=//rtsp_bridge:webrtc_streamer
third_party/ninja/ninja -C out/android-arm64 -j 8 rtsp_bridge:webrtc_streamer
mkdir -p "$WORKSPACE/dist/arm64-v8a" "$WORKSPACE/dist/include"
cp out/android-arm64/libwebrtc_streamer.so "$WORKSPACE/dist/arm64-v8a/"
cp "$WORKSPACE/android/include/webrtc_streamer.h" "$WORKSPACE/dist/include/"
file "$WORKSPACE/dist/arm64-v8a/libwebrtc_streamer.so"
third_party/llvm-build/Release+Asserts/bin/llvm-readelf -h -d -l \
  "$WORKSPACE/dist/arm64-v8a/libwebrtc_streamer.so" > "$WORKSPACE/logs/android-elf.txt"
third_party/llvm-build/Release+Asserts/bin/llvm-nm -D --defined-only \
  "$WORKSPACE/dist/arm64-v8a/libwebrtc_streamer.so" > "$WORKSPACE/logs/android-exports.txt"
sha256sum "$WORKSPACE/dist/arm64-v8a/libwebrtc_streamer.so"
python3 "$WORKSPACE/tools/audit_android_api.py"
python3 "$WORKSPACE/tools/audit_android_startup.py"
