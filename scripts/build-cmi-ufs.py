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

Enable it by listing it in board.toml [kernel] archives *before*
"component:ShengUfs", plus CONFIG_XNU_NATIVE_UFS=y and the [userdata] block.
Nothing calls it yet: cmi has not qualified storage.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    ROOT / 'drivers' / 'ShengUfs',
    ROOT / 'drivers' / 'NativeUfs',
]

# SM8550 offset -> SM8250 offset, applied in an order that cannot chain.
GCC_REWRITES = [
    (0x77018, 0x77010, 'GCC_UFS_PHY_AXI_ENABLE'),
    (0x77024, 0x77018, 'GCC_UFS_PHY_AHB_ENABLE'),
]


def find_tree() -> Path:
    for candidate in CANDIDATES:
        if candidate.is_dir():
            return candidate
    # The component may not be selected in this build; that is not a failure.
    print('== cmi ufs: ShengUfs tree not present, nothing to adapt')
    raise SystemExit(0)


def rewrite_offsets(text: str) -> tuple[str, int]:
    """Swap the two branch offsets without letting one rewrite feed the next."""
    sentinel_axi, sentinel_ahb = '0xCMIAXI', '0xCMIAHB'
    changes = 0
    pattern = re.compile(r'0x(77018|77024)\b')

    def replace(match):
        nonlocal changes
        value = int(match.group(1), 16)
        changes += 1
        if value == 0x77018:
            return sentinel_axi
        return sentinel_ahb

    text = pattern.sub(replace, text)
    text = text.replace(sentinel_axi, '0x77010').replace(sentinel_ahb, '0x77018')
    return text, changes


def main() -> int:
    tree = find_tree()
    gcc = tree / 'GccUfs.h'
    if not gcc.is_file():
        print('== cmi ufs: %s missing, nothing to adapt' % gcc)
        return 0
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

    for source in tree.glob('*.cpp'):
        text = source.read_text(encoding='utf-8', errors='replace')
        if 'qcom,sm8550-ufshc' not in text:
            continue
        source.write_text(text.replace('qcom,sm8550-ufshc', 'qcom,sm8250-ufshc'),
                          encoding='utf-8', newline='\n')
        print('== cmi ufs: %s now matches qcom,sm8250-ufshc' % source.name)
    return 0


if __name__ == '__main__':
    sys.exit(main())
