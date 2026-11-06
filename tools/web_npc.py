"""Данные для редактора сохранений web/save: python3 -m tools.web_npc → web/save/npc.js, items.png и maps/.

Номер NPC — id(N) скрипта диалога (он же номер персонажа в SAVEGAME/OBJLIST), имена — поле name. Для каждого
флага разговора (setBit/hasBit/clearBit(byte NPC, бит)) собираются места в скриптах, где он используется;
номер 235 в скрипте означает собеседника, то есть NPC этого же скрипта.

Предметы: номер типа → тайл (BASETILE) → название (LOOK, запись действует до своего тайла включительно), вес из
TILEFLAG (+0x1000); складываются в стопку те, у чьего английского названия есть множественное число (как в Nuvie).
Варианты предмета (кадры: цвет зелья, горящий факел, лунный камень конкретных врат) — тайлы от базового до
базового тайла следующего предмета, у каждого своё название в LOOK.
Иконки предметов: тайлы из tiles/ (MAPTILES.NNN — тайлы 0–511, OBJTILES.NNNN — тайл 512 + NNNN, увеличены в 10 раз),
уменьшенные до 16×16 и собранные в атлас items.png по ICONS_PER_ROW в ряд; у предмета — номер иконки icon.
Карты: maps/LZMAP.N.png (16 пикселей на клетку) уменьшаются до MAP_SCALE пикселей на клетку; поверхность режется на
куски MAP_PIECE×MAP_PIECE (раскладку повторяют MAP_PIECE и mapTiles в app.js). Результат web/save/maps/ не хранится
в git: его делает workflow Pages (или этот скрипт локально), пересобирается, только если исходник новее.
Яйца — невидимые объекты EGG на карте, из которых игра выпускает монстров (Nuvie, EggManager): из данных новой
игры (unpacked/LZOBJBLK — 64 файла OBJBLK поверхности подряд, LZDNGBLK — 5 файлов подземелий и шаблон OBJLIST).
Яйцо: [x, y, z, шанс %, качество (время * 10 + отношение), [[тип, до скольких], ...]]. Монстры (creatures) — типы
CREATURES с названием из LOOK и режимом поведения и отношением, которые чаще всего стоят у них в яйцах.
Тексты книг и свитков: book.json, качество предмета = номер текста + 1.
Заклинания: таблица названий в GAME.EXE, по 16 на круг (номер = (круг - 1) * 16 + номер в круге), перевод —
из patches/translation.json.
"""

import collections
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
MAP_SCALE = 4       # пикселей на клетку в картах страницы
MAP_PIECE = 1024    # сторона куска карты поверхности, пикселей
EGG = 335
# Монстры, животные и люди (их типы — в NOT_ITEMS), кроме частей тел: 366 — побег жгучей лозы, 425 — тело гидры.
CREATURES = [*range(342, 366), *range(367, 389), 411, 413, 424, *range(426, 431)]
DUNGEON_BLOCKS = 5
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


def build_maps(root, path):
    from PIL import Image

    os.makedirs(path, exist_ok=True)
    for level in range(6):
        source = os.path.join(root, 'maps', f'LZMAP.{level}.png')
        first = os.path.join(path, f'{level}_0_0.webp')
        if os.path.exists(first) and os.path.getmtime(first) >= os.path.getmtime(source):
            continue
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(source) as image:
            size = image.width // TILE * MAP_SCALE
            small = image.convert('RGB').resize((size, size), Image.BOX)
        # Имена кусков: уровень_ряд_столбец.webp; раскладку (размер, MAP_PIECE) страница знает сама — app.js, MAPS.
        for top in range(0, size, MAP_PIECE):
            for left in range(0, size, MAP_PIECE):
                name = f'{level}_{top // MAP_PIECE}_{left // MAP_PIECE}.webp'
                small.crop((left, top, left + MAP_PIECE, top + MAP_PIECE)).save(os.path.join(path, name), quality=85)
        print(f'{path}/{level}_*.webp: {size}×{size}')


def read_blocks(data, count=None):
    blocks = []
    position = 0
    while position < len(data) and (count is None or len(blocks) < count):
        n = int.from_bytes(data[position:position + 2], 'little')
        blocks.append([data[position + 2 + 8 * i:position + 10 + 8 * i] for i in range(n)])
        position += 2 + 8 * n
    return blocks


def collect_eggs(root):
    with open(os.path.join(root, 'unpacked', 'LZOBJBLK'), 'rb') as f:
        blocks = read_blocks(f.read())
    with open(os.path.join(root, 'unpacked', 'LZDNGBLK'), 'rb') as f:
        blocks += read_blocks(f.read(), DUNGEON_BLOCKS)
    eggs = []
    for records in blocks:
        for i, r in enumerate(records):
            if r[0] & 0x18 == 0 and r[4] | (r[5] & 3) << 8 == EGG:
                embryos = []
                for c in records[i + 1:]:
                    if c[0] & 0x18 != 0x08 or c[1] | (c[2] & 3) << 8 | (c[2] >> 2) << 10 != i:
                        break
                    embryos.append([c[4] | (c[5] & 3) << 8, c[6], c[7]])
                x, y, z = r[1] | (r[2] & 3) << 8, r[2] >> 2 | (r[3] & 0xf) << 6, r[3] >> 4
                eggs.append([x, y, z, r[6], r[7], embryos])
    return eggs


def collect_creatures(root, eggs):
    with open(os.path.join(root, 'unpacked', 'look.json')) as f:
        look = {int(k): v for k, v in json.load(f).items()}
    keys = sorted(look)
    with open(os.path.join(root, 'original', 'BASETILE'), 'rb') as f:
        basetile = f.read()
    worktypes = {}
    alignments = {}
    for *_, quality, embryos in eggs:
        for obj, _, worktype in embryos:
            worktypes.setdefault(obj, collections.Counter())[worktype] += 1
            alignments.setdefault(obj, collections.Counter())[quality % 10] += 1
    creatures = []
    for obj in CREATURES:
        tile = int.from_bytes(basetile[2 * obj:2 * obj + 2], 'little')
        name = look[next(k for k in keys if k >= tile)]
        creatures.append({
            'obj': obj,
            'english': singular(name['english']),
            'russian': singular(name['russian']),
            'worktype': worktypes[obj].most_common(1)[0][0] if obj in worktypes else 8,
            'alignment': alignments[obj].most_common(1)[0][0] if obj in alignments else 2,
        })
    return creatures


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
    build_maps(root, os.path.join(root, 'web', 'save', 'maps'))
    data['spells'] = collect_spells(root)
    data['books'] = collect_books(root)
    data['eggs'] = collect_eggs(root)
    data['creatures'] = collect_creatures(root, data['eggs'])
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    with open(path, 'w') as f:
        f.write('// Сгенерировано: python3 -m tools.web_npc. Не править руками.\n')
        f.write(f'window.NPC_DATA = {text};\n')
    print(f'{path}: {len(data["npcs"])} NPC, флаги для {len(data["flags"])} персонажей, '
          f'{len(data["items"])} предметов, {len(data["spells"])} заклинаний, {len(data["eggs"])} яиц')


if __name__ == '__main__':
    main()
