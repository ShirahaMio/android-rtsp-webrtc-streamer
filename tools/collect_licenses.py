"""Use upstream's dependency map with the actual GN binary, plus direct sources."""
from pathlib import Path
import os
import importlib.util
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get('WRS_BUILD_ROOT', '/opt/android-build')) / 'webrtc/src'
DEST = ROOT / 'dist/licenses'
DEST.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('upstream_licenses', SRC / 'tools_webrtc/libs/generate_licenses.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.LicenseBuilder._run_gn = staticmethod(lambda directory, target: subprocess.check_output([
    str(SRC / 'buildtools/linux64/gn'), 'desc', '--all', '--format=json', directory, target,
    '--root-target=//rtsp_bridge:webrtc_streamer'
], cwd=SRC, text=True))
builder = module.LicenseBuilder([str(SRC / 'out/android-arm64')], ['//rtsp_bridge:webrtc_streamer'])
libraries = builder._get_third_party_libraries(str(SRC / 'out/android-arm64'), '//rtsp_bridge:webrtc_streamer')
libraries |= {'webrtc', 'jsoncpp'}  # JSON is compiled directly to enable exceptions.
for name in sorted(libraries):
    if name not in builder.common_licenses_dict:
        raise RuntimeError(f'No upstream license mapping for {name}')
    for relative in builder.common_licenses_dict[name]:
        source = SRC / relative
        destination = DEST / 'webrtc' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
for path in ('LICENSE', 'PATENTS', 'AUTHORS'):
    shutil.copyfile(SRC / path, DEST / 'webrtc' / path)
for destination, source in {
    'webrtc-streamer-UNLICENSE': ROOT / 'upstream/UNLICENSE',
    'civetweb-LICENSE.md': ROOT / 'upstream/civetweb/LICENSE.md',
    'live555-COPYING': SRC / 'rtsp_bridge/live/COPYING',
    'live555-COPYING.LESSER': SRC / 'rtsp_bridge/live/COPYING.LESSER',
}.items():
    shutil.copyfile(source, DEST / destination)
(DEST / 'libraries.txt').write_text('\n'.join(sorted(libraries | {'civetweb', 'live555', 'live555helper', 'webrtc-streamer'})) + '\n')
print('Copied license files for', len(libraries), 'WebRTC dependency groups plus upstream RTSP/HTTP components')
