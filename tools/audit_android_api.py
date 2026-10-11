"""Verify every strong dynamic import against the API 28 NDK stub libraries."""
from pathlib import Path
import os
import json
import re
import subprocess

ROOT = Path(os.environ.get('WRS_BUILD_ROOT', '/opt/android-build')) / 'webrtc/src'
WORK = Path(__file__).resolve().parents[1]
READELF = ROOT / 'third_party/llvm-build/Release+Asserts/bin/llvm-readelf'
STUBS = ROOT / 'third_party/android_toolchain/ndk/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/28'
LIB = WORK / 'dist/arm64-v8a/libwebrtc_streamer.so'

def read(*args):
    return subprocess.check_output([str(READELF), *map(str, args)], text=True)

def symbols(path):
    for line in read('--dyn-syms', '--wide', path).splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[0].endswith(':') and fields[0][:-1].isdigit():
            yield fields[7].split('@')[0], fields[4], fields[6]

needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', read('-d', LIB))
available = set()
for name in needed:
    stub = STUBS / name
    assert stub.is_file(), f'Unexpected runtime dependency: {name}'
    available.update(name for name, binding, index in symbols(stub) if index != 'UND')
imports = [(name, bind) for name, bind, index in symbols(LIB) if index == 'UND']
missing = sorted(name for name, bind in imports if bind != 'WEAK' and name not in available)
weak_missing = sorted(name for name, bind in imports if bind == 'WEAK' and name not in available)
assert not missing, f'API 28 missing strong imports: {missing}'
assert not any(name == 'pthread_cond_clockwait' for name, _ in imports)
assert not re.search(r'^\s*TLS\s', read('-l', LIB), re.M), 'Native ELF TLS requires API 29'
exports = sorted(name for name, binding, index in symbols(LIB) if index != 'UND')
assert all(name.startswith(('wrs_', 'Java_com_example_rtsp_')) for name in exports)
report = {'minimum_android_api': 28, 'needed': needed, 'strong_imports_missing': missing,
          'weak_imports_missing': weak_missing, 'pthread_cond_clockwait_imported': False,
          'native_elf_tls': False, 'exports': exports, 'result': 'PASS',
          'weak_import_notes': 'BoringSSL allocator hooks test for null; compiler-rt CPU resolver tests memfd_create GOT for null (no call).',
          'scope': 'Static ELF/NDK ABI audit; not an Android device execution test'}
(WORK / 'logs/android-api28-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
