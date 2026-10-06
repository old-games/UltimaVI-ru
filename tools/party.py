import os
import re

# Шаблон savegame\objlist лежит в конце распакованного LZDNGBLK. Имена отряда — char[16][14] по +0xf00,
# номера NPC в отряде — по +0xfe0, размер отряда — по +0xff0. Имя Аватара (NPC 1) задаёт U.EXE, остальные
# спутники начального отряда (Dupre, Shamino, Iolo) берутся отсюда, а вступающие позже — из поля name
# их диалога (get_character_name.asm). Чтобы имена совпадали, берём перевод из того же поля name.
OBJLIST = 0xf1ea
NAMES = OBJLIST + 0xf00
NAME_SIZE = 14
ROSTER = OBJLIST + 0xfe0
COUNT = OBJLIST + 0xff0
AVATAR = 1


def get_names(conversations_path, language):
    names = {}
    for f in os.listdir(conversations_path):
        with open(os.path.join(conversations_path, f)) as s:
            script = s.read()
        match = re.search(r"^id\((\d+)\)\s*name\(\{\s*'english': '(.*?)',\s*'russian': '(.*?)'\s*\}\)", script, re.M)
        if match:
            names[int(match[1])] = match[2 if language == 'english' else 3]
    return names


def encode(data, conversations_path, language):
    if language == 'english':
        return data
    data = bytearray(data)
    assert data[NAMES:NAMES + NAME_SIZE].startswith(b'Avatar\x00')
    assert data[COUNT] == 4 and list(data[ROSTER:ROSTER + 4]) == [1, 2, 3, 4]
    names = get_names(conversations_path, language)
    for i in range(data[COUNT]):
        npc = data[ROSTER + i]
        if npc == AVATAR:
            continue
        o = NAMES + i * NAME_SIZE
        english = data[o:o + NAME_SIZE].split(b'\x00')[0].decode('ascii')
        assert english == get_names(conversations_path, 'english')[npc], f'NPC {npc}: {english}'
        name = names[npc].encode('cp866')
        assert len(name) < NAME_SIZE, f'NPC {npc}: {names[npc]} is longer than {NAME_SIZE - 1} bytes'
        data[o:o + NAME_SIZE] = name.ljust(NAME_SIZE, b'\x00')
    return bytes(data)
