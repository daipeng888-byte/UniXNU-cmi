#!/usr/bin/env python3
"""Provide the object names build-xnu-4k-baseline.sh's binding check expects.

build-virtio-mmio-bindings.py writes bindings.json next to lib<Canonical>.a but
compiles the concrete object as Native<Name>.o. The baseline script derives the
object name from the archive stem instead, so it looks for VirtioMmioBlock.o /
RamBlock.o. This creates byte-identical copies under those names; the recorded
compiled_object_sha256 then matches, which is exactly what the check verifies.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [
    ('build/virtio-mmio-block', 'NativeVirtioBlock.o', 'VirtioMmioBlock.o', 'libVirtioMmioBlock.a'),
    ('build/ram-block', 'NativeRamBlock.o', 'RamBlock.o', 'libRamBlock.a'),
]
for folder, source, alias, archive in PAIRS:
    out = ROOT / folder
    src, dst = out / source, out / alias
    record = json.loads((out / 'bindings.json').read_text())
    if not src.is_file():
        raise SystemExit(f'{src} missing: bindings cannot be qualified')
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if digest != record['compiled_object_sha256']:
        raise SystemExit(f'{src} does not match bindings.json')
    if not (out / archive).is_file():
        raise SystemExit(f'{out / archive} missing')
    shutil.copyfile(src, dst)
    print(f'PASS: {alias} <- {source} (sha256 {digest[:16]}...)')
