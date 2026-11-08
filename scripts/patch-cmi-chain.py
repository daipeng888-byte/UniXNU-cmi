#!/usr/bin/env python3
"""attempt-5: adapt ShengUfs + build-arm-driver.py to SM8250 bring-up.

Runs as the FIRST [kernel] archives recipe in the assembled build tree, before
``component:ShengUfs`` compiles. All rewrites are exact-match and idempotent;
a missing anchor is a hard build error (same convention as build-cmi-ufs.py).

Measured on the cmi handset 2026-11-08:
  * native-ufs-probe=7: nsmr=87 banks=74 sid0x60 match=ffff
    -> ShengUfs' hardcoded stream 0x60 (SM8550/sheng) is wrong for SM8250;
       the vendor DT routes UFS through 0xE0 (alioth.md:204, marble:50).
  * 2-byte binary patch 0x60 -> 0xE0 cleared SMMU and reached IOFindBSDRoot.
  * native-ufs-probe=10: SHNGROOT manifest status=0 windows=2 (UFS reads fine).
  * native-ufs-diagnostics=1: stage="policy count invalid", policies=0,
    prepared=0 published=0 -> the zero-policy CmiRootStub blocks publication.
  * Actual build chain is build-arm-driver.py with legacy_name="NativeUfs",
    which unconditionally adds -DNATIVE_VERIFIED_BLOCK=1. The arm64e-only
    build-sheng-source-storage.py is NOT used here.

So this script:
  1. Parameterises the SMMU stream (default 0xE0, boot-arg overridable).
  2. Ports marble's SMMU takeover (accept the firmware's translating bank).
  3. Ports marble's unverified publication branch into validate().
  4. Removes -DNATIVE_VERIFIED_BLOCK=1 from build-arm-driver.py so the driver
     compiles its explicit, boot-arg-gated unverified branch.
"""
import sys
from pathlib import Path

MARK = 'cmi-attempt5-v1'


def find_tree():
    for candidate in (Path.cwd(), Path(__file__).resolve().parents[1]):
        if (candidate / 'drivers' / 'ShengUfs' / 'NativeUfs.cpp').is_file():
            return candidate
    print('== cmi attempt5: build tree with drivers/ShengUfs not found', file=sys.stderr)
    raise SystemExit(1)


CPP_REWRITES = [
    ('// Give the UFS stream a pass-through mapping the way Linux does on this firmware.',
     '''// SM8250 routes the UFS host through apps-SMMU stream 0xE0; upstream
// ShengUfs hardcodes 0x60 (sheng / SM8550). Verified on cmi: the firmware's
// single valid SMR does not match 0x60, while 0xE0 clears SMMU readback.
static uint16_t ufsStreamId (void)
{
  unsigned stream = 0xE0;
  PE_parse_boot_argn ("native-ufs-stream", &stream, sizeof (stream));
  return static_cast<uint16_t> (stream);
}

// Give the UFS stream a pass-through mapping the way Linux does on this firmware.'''),
    ('smmuBypassStream (0x60, smmuMap, smmuReport, phys, 16384);',
     'smmuBypassStream (ufsStreamId (), smmuMap, smmuReport, phys, 16384);'),
    ('smmuBypassStream (0x60, gHost.smmuMap, report, gHost.phys, kDmaBytes);',
     'smmuBypassStream (ufsStreamId (), gHost.smmuMap, report, gHost.phys, kDmaBytes);'),
    ('(((smr ^ 0x60U) & 0x7fffU) & ~mask) == 0',
     '(((smr ^ ufsStreamId ()) & 0x7fffU) & ~mask) == 0'),
    ('static bool hostBringUp (const char **why)\n{\n',
     '''static bool hostBringUp (const char **why)
{
  unsigned takeover = 0;
  if (PE_parse_boot_argn ("native-ufs-smmu-takeover", &takeover, sizeof (takeover))) {
    gUfsSmmuTakeover = takeover != 0;
  }
'''),
    # Pinned upstream returns false unconditionally here; port marble's
    # explicit, boot-arg-gated development branch.
    # timerTicks() and the read/verify counters are defined INSIDE the
    # NATIVE_VERIFIED_BLOCK block upstream, but doAsyncReadWrite() references
    # them unconditionally outside it. Move them above that block so the
    # unverified build still compiles (this is the pinned upstream's own
    # latent bug, exposed only when the macro is off).
    ('volatile uint64_t native_ufs_verify_ticks = 0, native_ufs_read_ticks = 0;\n'
     'static inline uint64_t timerTicks (void) {uint64_t v; __asm__ volatile ("isb\\n\\tmrs %0, cntpct_el0" : "=r" (v)); return v;}\n'
     'volatile uint32_t native_ufs_integrity_failures = 0;',
     ''),
    ('// Data objects of the root image (version 2 manifest), recorded by startRoot before windows are configured.',
     '''// Timing/counter helpers live outside the verification block: the read path
// uses them in every build (upstream only ever compiled with the macro on).
volatile uint64_t native_ufs_verify_ticks = 0, native_ufs_read_ticks = 0;
static inline uint64_t timerTicks (void) {uint64_t v; __asm__ volatile ("isb\\n\\tmrs %0, cntpct_el0" : "=r" (v)); return v;}
volatile uint32_t native_ufs_integrity_failures = 0;

// Data objects of the root image (version 2 manifest), recorded by startRoot before windows are configured.'''),
    ('#else\n      return false; // Root publication requires owner verification in every build.\n#endif',
     '''#else
      uint32_t allowUnverified = 0;
      if (PE_parse_boot_argn ("native-ufs-allow-unverified", &allowUnverified, sizeof (allowUnverified)) &&
          allowUnverified == 1) {
        gRootDiagnostic.stage = "signed window identities (unverified allowed)";
        return true;
      }
      return false; // Root publication requires owner verification unless explicitly overridden.
#endif'''),
]

H_REWRITES = [
    ('  bool reuse = false;\n  const char *error = nullptr;\n};',
     '''  bool reuse = false;
  const char *error = nullptr;
};
// SM8250's firmware may leave the UFS stream on a translating context bank.
// With takeover enabled, an exclusive (mask 0) match on our own bank is
// accepted and configureUfsSmmu disables that context before reusing it.
static bool gUfsSmmuTakeover = false;'''),
    ('  uint32_t sctlr = read((p.pages + p.bank) * 4096);\n'
     '  if ((sctlr & 1) || (p.reuse && (sctlr || read(0x1000 + 4 * p.bank) != 0x10000 ||\n'
     '                                (read(0x1800 + 4 * p.bank) & ~1U)))) {\n'
     '    p.error = "reserved context bank not bypass"; return p;\n'
     '  }',
     '''  uint32_t sctlr = read((p.pages + p.bank) * 4096);
  bool takeover = gUfsSmmuTakeover && p.reuse;
  if (!takeover && ((sctlr & 1) || (p.reuse && (sctlr || read(0x1000 + 4 * p.bank) != 0x10000 ||
                                (read(0x1800 + 4 * p.bank) & ~1U))))) {
    p.error = "reserved context bank not bypass"; return p;
  }'''),
    ('  enum {kBankAttempts = 8};', '  enum {kBankAttempts = 128};'),
    ('  if (!p.reuse) write(cb, 0);', '  write(cb, 0);'),
    ('  if (!p.reuse) write(0x1000 + 4 * p.bank, 0x10000);',
     '  write(0x1000 + 4 * p.bank, 0x10000);'),
]

BUILD_DRIVER_OLD = """if component == 'NativeUfs':
    command += ['-I', str(ROOT / 'kits/VerifiedRoot/include'), '-I', str(ROOT / 'drivers/VirtioMmioBlock'),
                '-DNATIVE_VERIFIED_BLOCK=1', '-DNATIVE_VERIFIED_BLOCK_MULTI_POLICY=1', '-mgeneral-regs-only']"""
BUILD_DRIVER_NEW = """if component == 'NativeUfs':
    command += ['-I', str(ROOT / 'drivers/VirtioMmioBlock'), '-mgeneral-regs-only']
    # cmi bring-up: the owner-signed policy bundle is a later phase. Compile the
    # driver's explicit unverified branch, which still requires BOTH
    # native-ufs-allow-unverified=1 and root-unverified=1 at boot.
    if os.environ.get('XNU_VERIFIED_ROOT_PROBE', '0') == '1':
        command += ['-I', str(ROOT / 'kits/VerifiedRoot/include'),
                    '-DNATIVE_VERIFIED_BLOCK=1', '-DNATIVE_VERIFIED_BLOCK_MULTI_POLICY=1']"""


def apply(path, rewrites, marker=MARK, add_mark=True):
    text = path.read_text()
    if marker in text:
        print(f'== cmi attempt5: {path.name} already patched')
        return 0
    for old, new in rewrites:
        n = text.count(old)
        if n != 1:
            print(f'== cmi attempt5: {path.name}: anchor found {n} times: {old[:75]!r}', file=sys.stderr)
            raise SystemExit(1)
        text = text.replace(old, new)
    if add_mark:
        text = text.replace('// SPDX-License-Identifier: BSD-2-Clause-Patent',
                            '// SPDX-License-Identifier: BSD-2-Clause-Patent\n// ' + marker, 1)
    path.write_text(text)
    print(f'== cmi attempt5: patched {path.name} ({len(rewrites)} rewrites)')
    return len(rewrites)


def main():
    tree = find_tree()
    total = apply(tree / 'drivers' / 'ShengUfs' / 'NativeUfs.cpp', CPP_REWRITES)
    total += apply(tree / 'drivers' / 'ShengUfs' / 'SmmuTakeover.h', H_REWRITES)
    driver = tree / 'scripts' / 'build-arm-driver.py'
    text = driver.read_text()
    if MARK in text:
        print('== cmi attempt5: build-arm-driver.py already patched')
    else:
        if text.count(BUILD_DRIVER_OLD) != 1:
            print('== cmi attempt5: build-arm-driver.py anchor missing', file=sys.stderr)
            raise SystemExit(1)
        text = text.replace(BUILD_DRIVER_OLD, BUILD_DRIVER_NEW)
        # Keep the full compiler output so a -Werror failure is diagnosable.
        text = text.replace("raise SystemExit(result.stdout[-3500:])",
                            "raise SystemExit(result.stdout)")
        if 'import os' not in text:
            text = text.replace('import json\n', 'import json\nimport os\n', 1)
        text = text.replace('#!/usr/bin/env python3\n',
                            '#!/usr/bin/env python3\n# ' + MARK + ': SM8250 unverified bring-up\n', 1)
        driver.write_text(text)
        total += 1
        print('== cmi attempt5: patched build-arm-driver.py')
    print(f'== cmi attempt5: {total} rewrites applied at {tree}')


if __name__ == '__main__':
    main()
