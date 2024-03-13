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
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True, check=True)
        return r.stdout.rstrip()
    except Exception:
        return None


def get_binary_path(binary):
    path = f'unpacked/{binary}'
    if os.path.isfile(path):
        return path
    else:
        return f'original/{binary}'


def get_compressed_files():
    return [
        'ANIMMASK.VGA',
        'BLOCKS.SHP',
        'BOOTUP.M',
        'BRIT.M',
        'CGADRV.BIN',
        'CONVERT.PAL',
        'CREATE.M',
        'DUNGEON.M',
        'EEGADRV.BIN',
        'EGADRV.BIN',
        'END.M',
        'END.SHP',
        'ENGAGE.M',
        'FOREST.M',
        'GARGOYLE.M',
        'GYPSY.SHP',
        'HORNPIPE.M',
        'INTRO_1.SHP',
        'INTRO_2.SHP',
        'INTRO_3.SHP',
        'INTRO.M',
        'INTRO.PTR',
        'INTRO.SHP',
        'LOOK.LZD',
        'LZDNGBLK',
        'LZMAP',
        'LZOBJBLK',
        'MAINMENU.SHP',
        'MAPTILES.VGA',
        'MASKTYPE.VGA',
        'MCGADRV.BIN',
        'MONTAGE.SHP',
        'NEWMAGIC.BMP',
        'PAPER.BMP',
        'STARPOS.DAT',
        'STONES.M',
        'TGADRV.BIN',
        'TITLES.SHP',
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
    ]
