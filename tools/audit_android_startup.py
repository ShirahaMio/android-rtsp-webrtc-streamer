"""Check actual ELF constructors, including linked compiler runtime code."""
from pathlib import Path
import os
import json
import re
import struct
import subprocess

SRC = Path(os.environ.get('WRS_BUILD_ROOT', '/opt/android-build')) / 'webrtc/src'
WORK = Path(__file__).resolve().parents[1]
BIN = SRC / 'third_party/llvm-build/Release+Asserts/bin'
LIB = SRC / 'out/android-arm64/lib.unstripped/libwebrtc_streamer.so'
data = LIB.read_bytes()
assert data[:6] == b'\x7fELF\x02\x01'
shoff = struct.unpack_from('<Q', data, 40)[0]
entsize, count, names_index = struct.unpack_from('<HHH', data, 58)
sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + i * entsize) for i in range(count)]
names_section = sections[names_index]
names = data[names_section[4]:names_section[4] + names_section[5]]
constructors = []
relative_relocs = {}
dynamic = subprocess.check_output([str(BIN / 'llvm-readelf'), '-d', str(LIB)], text=True)
assert not re.search(r'\((?:ANDROID_RELA\w*|ANDROID_RELR\w*|RELR\w*)\)', dynamic), 'Packed relocations remain'
for section in sections:
    if section[1] == 4:  # SHT_RELA
        for pos in range(section[4], section[4] + section[5], section[9]):
            offset, info, addend = struct.unpack_from('<QQq', data, pos)
            if info == 1027:  # R_AARCH64_RELATIVE, symbol index zero
                relative_relocs[offset] = addend
for section in sections:
    name = names[section[0]:].split(b'\0', 1)[0]
    if name == b'.init_array':
        for offset in range(section[3], section[3] + section[5], 8):
            assert offset in relative_relocs, f'Missing standard constructor relocation: {offset:x}'
            constructors.append(relative_relocs[offset])
assert constructors
symbol_text = subprocess.check_output([str(BIN / 'llvm-nm'), '-S', '--defined-only', str(LIB)], text=True)
symbols = {}
for line in symbol_text.splitlines():
    fields = line.split()
    if len(fields) == 4:
        address, size = int(fields[0], 16), int(fields[1], 16)
        if size:
            symbols[address] = (size, fields[3])

bad = re.compile(r'\b(?:paciasp|pacibsp|autiasp|autibsp|pacia|pacib|autia|autib|retaa|retab|bti)\b')
checks = []
disassemblies = []
for address in constructors:
    assert address in symbols, f'Constructor missing symbol: {address:x}'
    size, name = symbols[address]
    code = subprocess.check_output([str(BIN / 'llvm-objdump'), '-d',
        f'--start-address={address}', f'--stop-address={address + size}', str(LIB)], text=True)
    assert not bad.search(code), f'PAC/BTI remains in constructor {name}'
    checks.append({'name': name, 'address': hex(address), 'bytes': size, 'pac_bti': False})
    disassemblies.append(code)
assert any(item['name'] == 'init_have_lse_atomics' for item in checks)
assert any(item['name'] == '__init_cpu_features' for item in checks)
gn_args = (SRC / 'out/android-arm64/args.gn').read_text()
assert 'arm_control_flow_integrity = "none"' in gn_args
report = {'result': 'PASS', 'checks': checks,
          'packed_relocations': False, 'all_constructors_have_standard_rela': True,
          'v03_log_rbx': '0x305f80', 'v03_matching_symbol': 'init_have_lse_atomics',
          'old_log_rbx': '0xc35600', 'old_v02_matching_symbol': 'init_have_lse_atomics',
          'scope': 'No PAC/BTI instructions in ELF constructor bodies; not a Houdini execution test'}
(WORK / 'logs/android-startup-audit.json').write_text(json.dumps(report, indent=2) + '\n')
(WORK / 'logs/android-startup-disassembly.txt').write_text('\n'.join(disassemblies))
print(json.dumps(report, indent=2))
