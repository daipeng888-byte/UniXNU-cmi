#!/usr/bin/env python3
"""Compile the board device tree into the firmware DTB the boot image needs.

board.toml [bootimg] dtb names build/cmi/cmi.dtb, which nothing else in the
package flow produces; [firmware] preflight runs this script with the build
tree as cwd and UNIXNU_DEVICE pointing at the device repository.

The include path needs the SoC dts directory as well as the board one, exactly
like the firmware workflow's dtc call:
    dtc -I dts -O dtb -i <soc>/dts -i <device>/dts -o build/cmi/cmi.dtb \
        <device>/dts/cmi.dts
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path('build/cmi/cmi.dtb')


def device_dir() -> Path:
    env = os.environ.get('UNIXNU_DEVICE')
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def soc_dts() -> Path:
    """Find the sm8250 feed's dts directory by walking up to out/feeds."""
    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        feeds = parent / 'feeds'
        if feeds.is_dir():
            for candidate in sorted(feeds.glob('*sm8250-common*')):
                dts = candidate / 'dts'
                if dts.is_dir():
                    return dts
    raise SystemExit('cannot locate the sm8250 feed dts directory from %s' % here)


def main() -> int:
    if shutil.which('dtc') is None:
        raise SystemExit('dtc is not on PATH')
    device = device_dir()
    source = device / 'dts' / 'cmi.dts'
    if not source.is_file():
        raise SystemExit('%s does not exist' % source)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    command = ['dtc', '-I', 'dts', '-O', 'dtb',
               '-i', str(soc_dts()), '-i', str(device / 'dts'),
               '-o', str(OUT), str(source)]
    print('+ ' + ' '.join(command), flush=True)
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit('dtc failed with %d' % result.returncode)
    print('== device tree: %s (%d bytes)' % (OUT.resolve(), OUT.stat().st_size))
    return 0


if __name__ == '__main__':
    sys.exit(main())
