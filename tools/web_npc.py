"""Данные о NPC для редактора сохранений web/save: python3 -m tools.web_npc → web/save/npc.js.

Номер NPC — id(N) скрипта диалога (он же номер персонажа в SAVEGAME/OBJLIST), имена — поле name. Для каждого
флага разговора (setBit/hasBit/clearBit(byte NPC, бит)) собираются места в скриптах, где он используется;
номер 235 в скрипте означает собеседника, то есть NPC этого же скрипта.
"""

import json
import os
import re

import tools

FLAG = re.compile(r"\b(hasBit|setBit|clearBit)\(byte (\d+), (?:value|byte) (\d+)\)")
NAME = re.compile(r"^id\((\d+)\)\s*name\(\{\s*'english': '(.*?)',\s*'russian': '(.*?)'\s*\}\)", re.M)
SELF = 235
OPERATIONS = {'hasBit': 'проверка', 'setBit': 'установка', 'clearBit': 'сброс'}


def collect(conversations_path):
    npcs = {}
    flags = {}
    for file_name in sorted(os.listdir(conversations_path)):
        with open(os.path.join(conversations_path, file_name)) as f:
            script = f.read()
        match = NAME.search(script)
        if match:
            npcs[int(match[1])] = {
                'id': int(match[1]),
                'english': match[2].replace("\\'", "'"),
                'russian': match[3].replace("\\'", "'"),
                'script': file_name,
            }
        for number, line in enumerate(script.splitlines(), 1):
            for operation, npc, bit in FLAG.findall(line):
                if int(npc) == SELF and match:
                    npc = match[1]
                flags.setdefault(npc, {}).setdefault(bit, []).append({
                    'script': file_name,
                    'line': number,
                    'operation': OPERATIONS[operation],
                    'text': line.strip(),
                })
    return {'npcs': [npcs[i] for i in sorted(npcs)], 'flags': flags}


def main():
    path = os.path.join(tools.get_script_path(), 'web', 'save', 'npc.js')
    data = collect(os.path.join(tools.get_script_path(), 'conversations'))
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    with open(path, 'w') as f:
        f.write('// Сгенерировано: python3 -m tools.web_npc. Не править руками.\n')
        f.write(f'window.NPC_DATA = {text};\n')
    print(f'{path}: {len(data["npcs"])} NPC, флаги для {len(data["flags"])} персонажей')


if __name__ == '__main__':
    main()
