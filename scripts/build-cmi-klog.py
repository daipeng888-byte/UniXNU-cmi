#!/usr/bin/env python3
"""Build the cmi boot-progress archive against the kernel's own compile flags.

The XNU build exports one <object>.json record per object (here startup.o). Reuse
its exact arguments so the archive matches the kernel ABI, then publish
build/boot-progress/libBootProgress.a, which is the path XNU_BOOT_PROGRESS links.
The same mechanism is what UniXNU-sheng uses for its diagnostic.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'boot-progress'
RECORD = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/osfmk/DEVELOPMENT/startup.o.json'
SOURCE = ROOT / 'kits/cmi/CmiKlog.c'


def main() -> int:
    if not RECORD.is_file():
        print('missing compile record: %s (build the kernel bootstrap pass first)' % RECORD,
              file=sys.stderr)
        return 1
    if not SOURCE.is_file():
        print('missing source: %s' % SOURCE, file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    record = json.loads(RECORD.read_text().strip().rstrip(','))
    obj = OUT / 'CmiKlog.o'
    command = []
    args = list(record['arguments'])
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == record['file']:
            command.append(str(SOURCE))
        elif arg in ('-o', '-MF', '-MT', '-MJ'):
            if arg == '-o':
                command += ['-o', str(obj)]
            index += 1
        elif arg == '-Xclang' and index + 1 < len(args) and args[index + 1].startswith('-W'):
            index += 1
        elif arg == '-D' and index + 1 < len(args) and args[index + 1].startswith('XNU_BOOT_PROGRESS='):
            index += 1
        elif not arg.startswith(('-W', '-DXNU_BOOT_PROGRESS=')):
            command.append(arg)
        index += 1
    command += ['-DXNU_BOOT_PROGRESS=1', '-mgeneral-regs-only', '-Wall', '-Wextra', '-Werror']
    print('+ ' + ' '.join(command[:6]) + ' ...', flush=True)
    subprocess.run(command, cwd=record['directory'], check=True, timeout=120)

    ar = shutil.which('ar') or shutil.which('llvm-ar')
    if ar is None:
        print('no ar/llvm-ar on PATH', file=sys.stderr)
        return 1
    archive = OUT / 'libBootProgress.a'
    archive.unlink(missing_ok=True)
    subprocess.run([ar, 'rcs', str(archive), str(obj)], check=True, timeout=60)
    (OUT / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
    print('== boot progress archive: %s (%d bytes)' % (archive, archive.stat().st_size))
    return 0


if __name__ == '__main__':
    sys.exit(main())
