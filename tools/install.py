"""Установка игры в каталог сборки — то же, что делает INSTALL.EXE при установке на жёсткий диск.

Без установки в дистрибутиве пустой MAP (карта мира) и нет SAVEGAME: игра, запущенная без INSTALL.EXE, стоит
посреди воды. Сверено байт в байт с установкой INSTALL.EXE в DOSBox (VGA/MCGA, мышь, AdLib 388):

- MAP — распакованный LZMAP;
- SAVEGAME/OBJBLK<x><y> — блоки объектов поверхности из LZOBJBLK (блок — u16 n и n записей по 8 байт), идут
  квадратами 2×2: блок i — x = (i // 4 % 4) * 2 + i % 2, y = i // 16 * 2 + i % 4 // 2, буквы A–H;
- SAVEGAME/OBJBLK<A–E>I — 5 подземелий из начала LZDNGBLK, SAVEGAME/OBJLIST — остаток LZDNGBLK (шаблон новой
  игры, в нём имена спутников, см. tools/party.py) и 256 нулевых байт;
- U6.8 — один нулевой байт, CONFIG.U6 — выбранные режимы (CONFIG).

Тестовая сборка для переводчиков — с уже созданным Аватаром (AVATAR): в OBJLIST те же байты, что пишет U.EXE при
создании персонажа (снято в DOSBox: мужчина, все ответы гадалке «А»), имя — AVATAR_NAME. Для русской версии — запуск
с клавиатурным драйвером: LAUNCHER.
"""

import os

import tools.file
import tools.lzw

# VGA/MCGA (v), мышь (m), AdLib (a), порт 388 — как в установке, по которой сверялось.
CONFIG = b'vma388'.ljust(20, b'\x00')
DUNGEONS = 5
OBJLIST_PADDING = 256
LETTERS = 'ABCDEFGH'
# Созданный персонаж: смещение в OBJLIST → (байт шаблона, байт после U.EXE). Имя — char[14] по NAME (см. tools/party.py).
AVATAR = {
    0x901: (15, 20),  # сила
    0xA01: (15, 17),  # ловкость
    0xB01: (15, 22),  # интеллект
    0xC02: (15, 114),  # опыт, u16 = 370
    0xC03: (39, 1),
    0xFF2: (8, 3),
    0x13F2: (30, 44),
    0x1C72: (0, 7),
}
AVATAR_NAME = 'Аватар'
NAME = 0xF00
NAME_SIZE = 14
# Клавиатурный драйвер UNIKBD с русской раскладкой (как в сборке для тестеров). ULTIMA6 без .BAT запустит
# ULTIMA6.EXE (DOS ищет .COM, .EXE, затем .BAT), поэтому у файла запуска своё имя.
LAUNCHER = 'U6RUS.BAT'
LAUNCHER_TEXT = b'@unikbd /sc /m:unikalt.std\r\n@ultima6.exe\r\n'
KEYBOARD_FILES = ('UNIKBD.COM', 'UNIKALT.STD')


def read_blocks(data, count=None):
    """→ ([блок байтами, с полем u16 n], позиция после последнего блока)."""
    blocks = []
    position = 0
    while position < len(data) and (count is None or len(blocks) < count):
        n = int.from_bytes(data[position : position + 2], 'little')
        blocks.append(data[position : position + 2 + 8 * n])
        position += 2 + 8 * n
    assert position <= len(data)
    return blocks, position


def surface_name(i):
    x = (i // 4 % 4) * 2 + i % 2
    y = i // 16 * 2 + i % 4 // 2
    return f'OBJBLK{LETTERS[x]}{LETTERS[y]}'


def create_avatar(objlist, name=AVATAR_NAME):
    objlist = bytearray(objlist)
    for offset, (old, new) in AVATAR.items():
        assert objlist[offset] == old, f'OBJLIST {offset:#x}: {objlist[offset]}, expected {old}'
        objlist[offset] = new
    assert objlist[NAME : NAME + NAME_SIZE].startswith(b'Avatar\x00')
    encoded = name.encode('cp866')
    assert 0 < len(encoded) < NAME_SIZE
    objlist[NAME : NAME + NAME_SIZE] = encoded.ljust(NAME_SIZE, b'\x00')
    return bytes(objlist)


def install(directory, launcher=False, avatar=False):
    """Каталог с файлами игры (LZMAP, LZOBJBLK, LZDNGBLK сжатые, как в дистрибутиве) → установленная игра."""

    def read(name):
        return tools.lzw.decompress(tools.file.read(os.path.join(directory, name)))

    tools.file.write(os.path.join(directory, 'MAP'), read('LZMAP'))
    tools.file.write(os.path.join(directory, 'U6.8'), b'\x00')
    tools.file.write(os.path.join(directory, 'CONFIG.U6'), CONFIG)
    savegame = os.path.join(directory, 'SAVEGAME')
    os.makedirs(savegame, exist_ok=True)
    surface, position = read_blocks(read('LZOBJBLK'))
    assert len(surface) == 64 and position == len(read('LZOBJBLK'))
    for i, block in enumerate(surface):
        tools.file.write(os.path.join(savegame, surface_name(i)), block)
    data = read('LZDNGBLK')
    dungeons, position = read_blocks(data, DUNGEONS)
    for i, block in enumerate(dungeons):
        tools.file.write(os.path.join(savegame, f'OBJBLK{LETTERS[i]}I'), block)
    objlist = data[position:] + bytes(OBJLIST_PADDING)
    tools.file.write(os.path.join(savegame, 'OBJLIST'), create_avatar(objlist) if avatar else objlist)
    if launcher:
        tools.file.write(os.path.join(directory, LAUNCHER), LAUNCHER_TEXT)
        for name in KEYBOARD_FILES:
            tools.file.write(
                os.path.join(directory, name), tools.file.read(os.path.join(tools.get_script_path(), 'tools', name))
            )
