#!/usr/bin/env bash
set -euo pipefail
ROOT="${WRS_BUILD_ROOT:-/opt/android-build}"
WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/tmp" "$WORKSPACE/logs"
export TMPDIR="$ROOT/tmp"
export XDG_CACHE_HOME="$ROOT/cache"
export PATH="/usr/bin:$ROOT/depot_tools:$PATH"
export DEPOT_TOOLS_UPDATE=0
cd "$ROOT/webrtc/src"
python3 "$WORKSPACE/tools/prepare_android_target.py" "$PWD"
mkdir -p out/linux-smoke
sed -e 's/target_os = "android"/target_os = "linux"/' \
    -e 's/target_cpu = "arm64"/target_cpu = "x64"/' \
    -e '/android_ndk_api_level/d' \
    -e '/arm_control_flow_integrity/d' \
    out/android-arm64/args.gn > out/linux-smoke/args.gn
buildtools/linux64/gn gen out/linux-smoke --root-target=//rtsp_bridge:webrtc_streamer
third_party/ninja/ninja -C out/linux-smoke -j 8 rtsp_bridge:webrtc_streamer
