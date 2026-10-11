#!/usr/bin/env bash
set -euo pipefail
ROOT="${WRS_BUILD_ROOT:-/opt/android-build}"
export TMPDIR="$ROOT/tmp"
export XDG_CACHE_HOME="$ROOT/cache"
export VPYTHON_VIRTUALENV_ROOT="$ROOT/cache/vpython"
export CIPD_CACHE_DIR="$ROOT/cache/cipd"
export DEPOT_TOOLS_UPDATE=0
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$ROOT/webrtc"
if [ ! -d "$ROOT/depot_tools/.git" ]; then
  git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git "$ROOT/depot_tools"
fi
export PATH="$ROOT/depot_tools:$PATH"
cd "$ROOT/webrtc"
if [ ! -f .gclient ]; then
  cat > .gclient <<'EOF'
solutions = [{
  'name': 'src',
  'url': 'https://webrtc.googlesource.com/src.git',
  'deps_file': 'DEPS',
  'managed': False,
  'custom_deps': {},
  'custom_vars': {'checkout_android': True, 'checkout_examples': False, 'checkout_tests': False},
}]
target_os = ['android']
EOF
fi
gclient sync --no-history --nohooks --revision src@848836f85d4036def631df0ed6eeb001b5c0c174 -j 8
# This standalone library does not use upstream audio/video test fixtures.
python3 - <<'PY'
from pathlib import Path
p = Path('src/DEPS')
s = p.read_text()
needle = "# Download test resources, i.e. video and audio files from Google Storage."
if needle + "\n    'condition': 'False'," not in s:
    if s.count(needle) != 1:
        raise RuntimeError('Unexpected WebRTC test-resource hook')
    p.write_text(s.replace(needle, needle + "\n    'condition': 'False',"))
PY
gclient runhooks
