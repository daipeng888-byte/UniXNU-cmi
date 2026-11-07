#!/usr/bin/env python3
"""Install the pinned IOBlockStorageDevice ABI audit as a kernel build input.

audit-storage-interface.py derives this record from a live QEMU guest and the
original prelinked kernelcache; neither exists on a CI runner. The record is a
property of the OS profile kernelcache (iPadOS 17.7.11 / 21H461), so it is
shipped with the device repository and consumed verbatim -- exactly how
build-virtio-mmio-bindings.py treats it ("the audit JSON is the pinned record").
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve().parent / 'data' / 'interface-audit.json'
TARGET = ROOT / 'build' / 'storage-abi' / 'interface-audit.json'

record = json.loads(SOURCE.read_text())
checks = {
    'public_source_revision': 'e45fbe30a7879e0b16e26dddb78538f1b00e0bff',
    'method_slots': 190,
    'kernel_bindings': 176,
    'live_native_4k': True,
    'abstract_complete_destructors_trap': True,
}
if any(record.get(k) != v for k, v in checks.items()) or len(record.get('methods', [])) != 190:
    raise SystemExit('pinned storage ABI audit failed qualification')
TARGET.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(SOURCE, TARGET)
print(f'PASS: pinned storage ABI audit installed at {TARGET}')
