#!/usr/bin/env python3
"""Cross-compile the development-only unverified root lookup archive."""
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/cmi-unverified-root'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(__file__).resolve().parent / 'CmiUnverifiedRoot.cpp'
RECORD = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
if not SOURCE.is_file():
    raise SystemExit(f'{SOURCE} is missing')
if not RECORD.is_file():
    raise SystemExit(f'missing compile record {RECORD}; run a kernel build first')
record = json.loads(RECORD.read_text().strip().rstrip(','))
obj = OUT / 'CmiUnverifiedRoot.o'
command = []
args = record['arguments']
index = 0
while index < len(args):
    value = args[index]
    if value == record['file']:
        command.append(str(SOURCE))
    elif value == '-o':
        command.extend(['-o', str(obj)]); index += 1
    elif value in ('-MF', '-MJ'):
        index += 1
    elif value not in ('-MD', '-MP'):
        command.append(value)
    index += 1
command += ['-I', str(SOURCE.parent), '-Wno-unused-parameter']
result = subprocess.run(command, cwd=record['directory'], capture_output=True, text=True)
(OUT / 'compile.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit((result.stdout + result.stderr)[-3500:])
archive = OUT / 'libCmiUnverifiedRoot.a'
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', str(archive), str(obj)], check=True)
(OUT / 'build-report.json').write_text(json.dumps({
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'verified_root': False,
    'boot_args_required': ['native-ufs-allow-unverified=1', 'root-unverified=1'],
}, indent=2) + '\n')
print(f'PASS: unverified root lookup {archive} ({archive.stat().st_size} bytes)')
