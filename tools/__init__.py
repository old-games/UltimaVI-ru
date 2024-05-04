import os
import subprocess


def get_binaries():
    return [
        'GAME.EXE',
        'END.EXE',
        'INSTALL.EXE',
        'U.EXE',
    ]


def get_sha():
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True, check=True).stdout.rstrip()
    except Exception:
        return None


def get_script_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_path(name, current_directory='.'):
    paths = [
        os.path.join(current_directory, name),
        os.path.join(get_script_path(), 'unpacked', name),
    ]
    if name not in get_compressed_files():
        paths.append(os.path.join(get_script_path(), 'original', name))
    for path in paths:
        if os.path.isfile(path):
            return path


def get_force_original_files():
    return (
        'MAPTILES.VGA',
    )


def get_compressed_files():
    return (
        'ANIMMASK.VGA',
        'BOOTUP.M',
        'BRIT.M',
        'CGADRV.BIN',
        'CONVERT.PAL',
        'CREATE.M',
        'DUNGEON.M',
        'EEGADRV.BIN',
        'EGADRV.BIN',
        'END.M',
        'ENGAGE.M',
        'FOREST.M',
        'GARGOYLE.M',
        'HORNPIPE.M',
        'INTRO.M',
        'INTRO.PTR',
        'LZDNGBLK',
        'LZMAP',
        'LZOBJBLK',
        'MAPTILES.VGA',
        'MASKTYPE.VGA',
        'MCGADRV.BIN',
        'NEWMAGIC.BMP',
        'PAPER.BMP',
        'STARPOS.DAT',
        'STONES.M',
        'TGADRV.BIN',
        'U6.SET',
        'U6ADLIB.DRV',
        'U6CGA.DRV',
        'U6CMS.DRV',
        'U6COVOX.DRV',
        'U6CURS.CGA',
        'U6CURS.EGA',
        'U6CURS.TGA',
        'U6EGA.DRV',
        'U6INNOVA.DRV',
        'U6MCGA.DRV',
        'U6MCGA.PTR',
        'U6ROLAND.DRV',
        'U6TANDY.DRV',
        'U6TMUS.DRV',
        'ULTIMA.M',
        'WORLDMAP.BMP',
    )


def get_compressed_executables():
    return (
        'END.EXE',
        'GAME.EXE',
        'INSTALL.EXE',
        'MAKEMODE.EXE',
        'T2CGA.EXE',
        'T2EGA.EXE',
        'T2HRC.EXE',
        'T2TGA.EXE',
        'TANDYPIN.EXE',
        'U.EXE',
        'ULTIMA6.EXE',
    )


def get_archive_files():
    return (
        'CONVERSE.A',
        'CONVERSE.B',
        'PORTRAIT.A',
        'PORTRAIT.B',
        'PORTRAIT.Z',
    )
