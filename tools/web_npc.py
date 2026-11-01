"""Данные для редактора сохранений web/save: python3 -m tools.web_npc → web/save/npc.js и web/save/items.png.

Номер NPC — id(N) скрипта диалога (он же номер персонажа в SAVEGAME/OBJLIST), имена — поле name. Для каждого
флага разговора (setBit/hasBit/clearBit(byte NPC, бит)) собираются места в скриптах, где он используется;
номер 235 в скрипте означает собеседника, то есть NPC этого же скрипта.

Предметы: номер типа → тайл (BASETILE) → название (LOOK, запись действует до своего тайла включительно), вес из
TILEFLAG (+0x1000); складываются в стопку те, у чьего английского названия есть множественное число (как в Nuvie).
Варианты предмета (кадры: цвет зелья, горящий факел, лунный камень конкретных врат) — тайлы от базового до
базового тайла следующего предмета, у каждого своё название в LOOK.
Иконки предметов: тайлы из tiles/ (MAPTILES.NNN — тайлы 0–511, OBJTILES.NNNN — тайл 512 + NNNN, увеличены в 10 раз),
уменьшенные до 16×16 и собранные в атлас items.png по ICONS_PER_ROW в ряд; у предмета — номер иконки icon.
Тексты книг и свитков: book.json, качество предмета = номер текста + 1.
Заклинания: таблица названий в GAME.EXE, по 16 на круг (номер = (круг - 1) * 16 + номер в круге), перевод —
из patches/translation.json.
"""

import json
import os
import re

import tools

FLAG = re.compile(r"\b(hasBit|setBit|clearBit)\(byte (\d+), (?:value|byte) (\d+)\)")
NAME = re.compile(r"^id\((\d+)\)\s*name\(\{\s*'english': '(.*?)',\s*'russian': '(.*?)'\s*\}\)", re.M)
SELF = 235
NOT_ITEMS = {*range(339, 389), 409, 410, 411}     # тела, существа, люди, Лорд Бритиш, Аватар, дракон
SPELL_NAMES = 203380                               # файл GAME.EXE: 128 указателей на названия заклинаний
GAME_DS = 200272
TILE = 16
ICONS_PER_ROW = 32
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


def singular(name):
    # "gold coin\\s", "золот/ая\\ые монет/а\\ы": "\\..." — окончание множественного числа, "/" — начало единственного.
    return re.sub(r'\\[^\s/]*', '', name).replace('/', '')


def collect_items(root):
    with open(os.path.join(root, 'unpacked', 'look.json')) as f:
        look = {int(k): v for k, v in json.load(f).items()}
    keys = sorted(look)
    with open(os.path.join(root, 'original', 'BASETILE'), 'rb') as f:
        basetile = f.read()
    with open(os.path.join(root, 'original', 'TILEFLAG'), 'rb') as f:
        tileflag = f.read()
    bases = [int.from_bytes(basetile[2 * obj:2 * obj + 2], 'little') for obj in range(1024)]
    tiles = sorted(set(bases))
    items = []
    for obj in range(1, 1024):
        weight = tileflag[0x1000 + obj]
        if not weight or obj in NOT_ITEMS:
            continue
        tile = bases[obj]
        frames = min(next((t for t in tiles if t > tile), tile + 1) - tile, 64)
        names = [look[next(k for k in keys if k >= tile + frame)] for frame in range(frames)]
        same = len({name['english'] for name in names}) == 1
        for frame, name in enumerate(names):
            suffix = f' (вариант {frame + 1})' if frames > 1 and same else ''
            items.append({
                'obj': obj,
                'frame': frame,
                'tile': tile + frame,
                'english': singular(name['english']) + suffix.replace('вариант', 'variant'),
                'russian': singular(name['russian']) + suffix,
                'stackable': '\\' in names[0]['english'],
                'weight': weight,
            })
    return items


def tile_path(root, tile):
    name = f'MAPTILES.{tile:03}.VGA.png' if tile < 512 else f'OBJTILES.{tile - 512:04}.VGA.png'
    return os.path.join(root, 'tiles', name)


def build_icons(root, items, path):
    from PIL import Image

    rows = (len(items) + ICONS_PER_ROW - 1) // ICONS_PER_ROW
    atlas = Image.new('RGBA', (ICONS_PER_ROW * TILE, rows * TILE))
    for icon, item in enumerate(items):
        with Image.open(tile_path(root, item.pop('tile'))) as tile:
            small = tile.convert('RGBA').resize((TILE, TILE), Image.NEAREST)
        atlas.paste(small, (icon % ICONS_PER_ROW * TILE, icon // ICONS_PER_ROW * TILE))
        item['icon'] = icon
    atlas.save(path, optimize=True)


def collect_books(root):
    with open(os.path.join(root, 'unpacked', 'book.json')) as f:
        books = json.load(f)

    def first(lines):
        return next((line.strip() for line in lines if line.strip()), '')[:70]

    return [
        {'quality': i + 1, 'english': first(book['english']), 'russian': first(book['russian'])}
        for i, book in enumerate(books)
    ]


def collect_spells(root):
    with open(os.path.join(root, 'unpacked', 'GAME.EXE'), 'rb') as f:
        game = f.read()
    with open(os.path.join(root, 'patches', 'translation.json')) as f:
        translation = {x['offset']: x for x in json.load(f) if x['source'] == 'GAME.EXE'}
    spells = []
    for number in range(128):
        pointer = int.from_bytes(game[SPELL_NAMES + 2 * number:SPELL_NAMES + 2 * number + 2], 'little')
        offset = GAME_DS + pointer
        english = game[offset:game.index(b'\0', offset)].decode('ascii')
        if not english:
            continue
        russian = translation.get(offset, {}).get('russian', english)
        spells.append({
            'number': number,
            'circle': number // 16 + 1,
            'english': english,
            'russian': english if russian.startswith('FIXME ') else russian,
        })
    return spells


def main():
    path = os.path.join(tools.get_script_path(), 'web', 'save', 'npc.js')
    root = tools.get_script_path()
    data = collect(os.path.join(root, 'conversations'))
    data['items'] = collect_items(root)
    build_icons(root, data['items'], os.path.join(root, 'web', 'save', 'items.png'))
    data['spells'] = collect_spells(root)
    data['books'] = collect_books(root)
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    with open(path, 'w') as f:
        f.write('// Сгенерировано: python3 -m tools.web_npc. Не править руками.\n')
        f.write(f'window.NPC_DATA = {text};\n')
    print(f'{path}: {len(data["npcs"])} NPC, флаги для {len(data["flags"])} персонажей, '
          f'{len(data["items"])} предметов, {len(data["spells"])} заклинаний')


if __name__ == '__main__':
    main()
