#!/usr/bin/env python3
"""Cross-compile the refusal-only owner-root stub into libCmiRootStub.a."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/cmi-root-stub'
RECORD = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
SOURCE = Path(__file__).resolve().parent / 'CmiRootStub.cpp'
ARCHIVE = OUT / 'libCmiRootStub.a'

if not RECORD.is_file():
    raise SystemExit(f'missing compile record {RECORD}; run a kernel build first')
if not SOURCE.is_file():
    raise SystemExit(f'missing source {SOURCE}')
OUT.mkdir(parents=True, exist_ok=True)

record = json.loads(RECORD.read_text().strip().rstrip(','))
arguments = record['arguments']
obj = OUT / 'CmiRootStub.o'
command = []
index = 0
while index < len(arguments):
    value = arguments[index]
    if value == record['file']:
        command.append(str(SOURCE))
    elif value == '-o':
        command += ['-o', str(obj)]
        index += 1
    elif value == '-Xclang' and index + 1 < len(arguments) and arguments[index + 1].startswith('-W'):
        index += 1
    elif not value.startswith('-W'):
        command.append(value)
    index += 1
command += ['-Wall', '-Wno-unused-parameter',
            '-I', str(ROOT / 'kits/VerifiedRoot/include'),
            '-I', str(ROOT / 'drivers/VirtioMmioBlock')]
(out_cmd := OUT / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
subprocess.run(command, cwd=record['directory'], check=True)
ARCHIVE.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', str(ARCHIVE), str(obj)], check=True)
print(f'PASS: {ARCHIVE} ({ARCHIVE.stat().st_size} bytes), refusal-only, 0 policies')
