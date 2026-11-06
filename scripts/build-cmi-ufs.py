#!/usr/bin/env python3
"""Adapt the fetched ShengUfs component to this board's SM8250 UFS controller.

ShengUfs is written for SM8550. The UFS controller itself sits at the same
address on both SoCs (0x1d84000/0x3000) and the GCC UFS register block is at the
same relative offset (gcc + 0x77000 = 0x177000), but two branch enables moved.
reAAAq/UniXNU-umi proves the SM8250 values on this firmware:

    GDSCR       0x77004  bit31   (same)
    AXI enable  0x77010  bit0    (SM8550 has 0x77018)
    AHB enable  0x77018  bit0    (SM8550 has 0x77024)

The script rewrites the fetched tree in place, before the component archive
build runs, so the shared component stays untouched upstream. It is idempotent:
re-running on an already patched tree prints "already patched".

It runs as a [kernel] archives recipe with the build tree as cwd, the same
convention scripts/build-cmi-dtb.py documents for preflight, and the shared
build tool fetches the component to <tree>/drivers/ShengUfs. So the tree is
located from cwd first, then from the script location, then by walking up.

The script is self-checking on purpose: being listed in archives means ShengUfs
*is* selected, so a tree that cannot be found, or a rewrite that did not land,
is a build error rather than a silent no-op. A silent no-op would still link a
kernel -- with SM8550 offsets that only fail on the handset.
"""
import os
import re
import sys
from pathlib import Path

COMPATIBLE_FROM = 'qcom,sm8550-ufshc'
COMPATIBLE_TO = 'qcom,sm8250-ufshc'

# SM8550 offset -> SM8250 offset, applied in an order that cannot chain.
GCC_REWRITES = [
    (0x77018, 0x77010, 'GCC_UFS_PHY_AXI_ENABLE'),
    (0x77024, 0x77018, 'GCC_UFS_PHY_AHB_ENABLE'),
]


def candidates():
    """Every plausible <tree>/drivers/ShengUfs, most likely first, deduplicated."""
    seen = []

    def add(path):
        resolved = path.resolve()
        if resolved not in seen:
            seen.append(resolved)

    add(Path.cwd() / 'drivers' / 'ShengUfs')
    for parent in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        add(parent / 'drivers' / 'ShengUfs')
    here = Path(__file__).resolve()
    add(here.parents[1] / 'drivers' / 'ShengUfs')      # <tree>/scripts/build-cmi-ufs.py
    add(here.parents[0] / 'drivers' / 'ShengUfs')      # <tree>/build-cmi-ufs.py
    env = os.environ.get('UNIXNU_TREE')
    if env:
        add(Path(env) / 'drivers' / 'ShengUfs')
    return seen


def find_tree():
    tried = candidates()
    for candidate in tried:
        if candidate.is_dir():
            return candidate
    print('== cmi ufs: ShengUfs tree not found, so the SM8250 offsets cannot be applied:', file=sys.stderr)
    for candidate in tried:
        print('   tried %s' % candidate, file=sys.stderr)
    print('== cmi ufs: expected fetch to place drivers/ShengUfs and the recipe to run with the build tree as cwd', file=sys.stderr)
    raise SystemExit(1)


def rewrite_offsets(text):
    """Swap the two branch offsets without letting one rewrite feed the next."""
    sentinel_axi, sentinel_ahb = '0xCMIAXI', '0xCMIAHB'
    changes = 0
    pattern = re.compile(r'0x(77018|77024)\b')

    def replace(match):
        nonlocal changes
        changes += 1
        return sentinel_axi if int(match.group(1), 16) == 0x77018 else sentinel_ahb

    text = pattern.sub(replace, text)
    return text.replace(sentinel_axi, '0x77010').replace(sentinel_ahb, '0x77018'), changes


def problems(text):
    found = []
    if '0x77010' not in text:
        found.append('SM8250 AXI enable 0x77010 missing')
    if not re.search(r'GCC_UFS_PHY_AHB_ENABLE\s+0x77018\b', text):
        found.append('SM8250 AHB enable 0x77018 missing')
    if '0x77024' in text:
        found.append('SM8550 AHB offset 0x77024 still present')
    return found


def main():
    tree = find_tree()
    gcc = tree / 'GccUfs.h'
    if not gcc.is_file():
        print('== cmi ufs: %s missing; the component layout changed' % gcc, file=sys.stderr)
        return 1

    original = gcc.read_text(encoding='utf-8', errors='replace')
    if 'cmi: SM8250' in original:
        print('== cmi ufs: GccUfs.h already patched')
    else:
        patched, changes = rewrite_offsets(original)
        if changes == 0:
            print('== cmi ufs: offsets not found in GccUfs.h; the component changed', file=sys.stderr)
            return 1
        patched = patched.replace(
            '#ifndef NATIVE_UFS_GCC_UFS_H',
            '// cmi: SM8250 branch enables (0x77010 AXI, 0x77018 AHB); the GDSCR\n'
            '// offset 0x77004 is identical on SM8550 and SM8250, per umi.\n'
            '#ifndef NATIVE_UFS_GCC_UFS_H',
            1)
        gcc.write_text(patched, encoding='utf-8', newline='\n')
        print('== cmi ufs: rewrote %d GCC offset(s) in %s' % (changes, gcc))

    for source in sorted(tree.glob('*.cpp')):
        text = source.read_text(encoding='utf-8', errors='replace')
        if COMPATIBLE_FROM not in text:
            continue
        source.write_text(text.replace(COMPATIBLE_FROM, COMPATIBLE_TO), encoding='utf-8', newline='\n')
        print('== cmi ufs: %s now matches %s' % (source.name, COMPATIBLE_TO))

    # Never report success unless the tree really carries the SM8250 values.
    bad = problems(gcc.read_text(encoding='utf-8', errors='replace'))
    if bad:
        print('== cmi ufs: GccUfs.h is not adapted: %s' % '; '.join(bad), file=sys.stderr)
        return 1
    sources = sorted(tree.glob('*.cpp'))
    stale = [s.name for s in sources if COMPATIBLE_FROM in s.read_text(encoding='utf-8', errors='replace')]
    if stale:
        print('== cmi ufs: %s still names %s' % (', '.join(stale), COMPATIBLE_FROM), file=sys.stderr)
        return 1
    if not any(COMPATIBLE_TO in s.read_text(encoding='utf-8', errors='replace') for s in sources):
        print('== cmi ufs: no source matches %s; the personality changed' % COMPATIBLE_TO, file=sys.stderr)
        return 1
    print('== cmi ufs: SM8250 adaptation verified in %s' % tree)
    return 0


if __name__ == '__main__':
    sys.exit(main())
