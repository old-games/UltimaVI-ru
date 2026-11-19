"""Графика в архивах *.SHP (заставка, меню, создание персонажа) ⇄ PNG для «Системы Переводчик».

Архив SHP сжат LZW (tools.lzw). Внутри: u32 размер, таблица u32 смещений кадров (от начала, вместе с полем
размера; 0 — кадра нет), кадры. tools.archive.decode для SHP режет со сдвигом на 4 байта (смещения считает от
конца поля размера) — поэтому свой разбор.

Кадр: s16 right, left, top, bottom (кадр от -left..right по x и -top..bottom по y), затем строки:
u16 n, s16 x, s16 y; n чётное — n/2 пикселей подряд как есть, нечётное — n/2 пикселей сериями: байт c, нечётный —
повтор следующего байта c/2 раз, чётный — c/2 байт как есть. Конец кадра — n = 0. Незакрашенные места прозрачны.

PNG: indexed, палитра игры (у каждого архива своя, см. PALETTES), прозрачный — индекс 255 (ни в одном архиве игры
не используется). Размер картинки — (left + right + 1) × (top + bottom + 1).

python3 -m tools.shapes export <каталог игры> <каталог PNG> [АРХИВ[:кадр,кадр…] …]
    Кадры в PNG: <каталог PNG>/<АРХИВ>.SHP/<NNN>.png. Без списка — TEXT_FRAMES (кадры с текстом).
    --changed <каталог оригинала> — только кадры, отличающиеся от оригинала (перерисовки из готовой сборки).

python3 -m tools.shapes import <выгрузка СП: project.zip или каталог> [каталог графики, по умолчанию graphics]
    Ищет PNG по путям <АРХИВ>.SHP/<NNN>.png (папка графического перевода — любая), проверяет палитру и прозрачность,
    кладёт в graphics/ только отличающиеся от оригинала кадры; лишние PNG в graphics/ удаляет.

Сборка (tools.build, русские данные) берёт graphics/: изменённые архивы собираются заново, неизменённые кадры —
байты оригинала, кадров без PNG — оригинал.
"""

import io
import os
import re
import sys
import zipfile

from PIL import Image

import tools
import tools.file
import tools.lzw

TRANSPARENT = 255
GRAPHICS = 'graphics'
PATH = re.compile(r'(?:^|/)([A-Z0-9_]+\.SHP)/(\d{3})\.png$', re.IGNORECASE)

# Палитра архива: U6PAL или N-я палитра PALETTES.INT. Определены по скриншотам игры (U.EXE): сцены заставки — 1,
# гадалка — 4, меню и создание персонажа — U6PAL. Логотип ORIGIN и «Lord British» совпадают с несколькими палитрами.
PALETTES = {
    'GYPSY.SHP': 4,
    'INTRO_1.SHP': 1,
    'MAINMENU.SHP': 'U6PAL',
    'TITLES.SHP': 'U6PAL',
    'VELLUM1.SHP': 'U6PAL',
}

# Кадры с надписями (просмотрены все кадры всех SHP). Цифры заставки (INTRO_1 2–11) и руны на стене (INTRO 5) не
# переводятся.
TEXT_FRAMES = {
    'GYPSY.SHP': [7, 8],  # кнопки ответов A/B
    'INTRO_1.SHP': [53, 54, 65, 69, 70],  # PLEDGE NOW!, телефон, титры на экране, ORIGIN Presents, A Lord British Production
    'MAINMENU.SHP': [0],
    'TITLES.SHP': [0, 1],  # Ultima VI, The False Prophet
    'VELLUM1.SHP': list(range(1, 19)),  # кнопки создания персонажа и буквы A–K
}


def read_archive(data):
    """Сжатый архив → список кадров (bytes или None)."""
    data = tools.lzw.decompress(data)
    assert int.from_bytes(data[:4], 'little') == len(data)
    offsets = []
    position = 4
    while not any(offsets) or position < min(offset for offset in offsets if offset):
        offsets.append(int.from_bytes(data[position : position + 4], 'little'))
        position += 4
    starts = sorted(set(offset for offset in offsets if offset)) + [len(data)]
    ends = dict(zip(starts, starts[1:]))
    return [bytes(data[offset : ends[offset]]) if offset else None for offset in offsets]


def write_archive(frames):
    """Список кадров → несжатый архив (сжимает сборка)."""
    offset = 4 + 4 * len(frames)
    table = bytearray()
    body = bytearray()
    for frame in frames:
        table += (offset + len(body) if frame is not None else 0).to_bytes(4, 'little')
        body += frame or b''
    size = 4 + len(table) + len(body)
    return size.to_bytes(4, 'little') + table + body


def decode_frame(frame):
    """→ ((right, left, top, bottom), {(x, y): индекс})"""
    bounds = tuple(int.from_bytes(frame[i : i + 2], 'little', signed=True) for i in (0, 2, 4, 6))
    pixels = {}
    i = 8
    while True:
        n = int.from_bytes(frame[i : i + 2], 'little')
        i += 2
        if n == 0:
            break
        x = int.from_bytes(frame[i : i + 2], 'little', signed=True)
        y = int.from_bytes(frame[i + 2 : i + 4], 'little', signed=True)
        i += 4
        count = n >> 1
        if not n & 1:
            for k in range(count):
                pixels[(x + k, y)] = frame[i + k]
            i += count
            continue
        done = 0
        while done < count:
            c = frame[i]
            i += 1
            m = c >> 1
            for k in range(m):
                pixels[(x + done + k, y)] = frame[i] if c & 1 else frame[i + k]
            i += 1 if c & 1 else m
            done += m
        assert done == count, f'Run overflows the line: {done} > {count}'
    assert i == len(frame), f'Trailing bytes: {len(frame) - i}'
    return bounds, pixels


def _encode_runs(values):
    result = bytearray()
    literal = []

    def flush():
        while literal:
            chunk = literal[:127]
            del literal[:127]
            result.append(len(chunk) * 2)
            result.extend(chunk)

    i = 0
    while i < len(values):
        j = i
        while j < len(values) and values[j] == values[i] and j - i < 127:
            j += 1
        if j - i >= 3:
            flush()
            result.append((j - i) * 2 + 1)
            result.append(values[i])
            i = j
        else:
            literal.append(values[i])
            i += 1
    flush()
    return result


def encode_frame(bounds, pixels):
    result = bytearray()
    for value in bounds:
        result += value.to_bytes(2, 'little', signed=True)
    for y in sorted({y for x, y in pixels}):
        xs = sorted(x for x, yy in pixels if yy == y)
        start = 0
        while start < len(xs):
            end = start
            while end + 1 < len(xs) and xs[end + 1] == xs[end] + 1 and end + 1 - start < 0x3fff:
                end += 1
            values = [pixels[(x, y)] for x in xs[start : end + 1]]
            runs = _encode_runs(values)
            if len(runs) < len(values):
                result += (len(values) * 2 + 1).to_bytes(2, 'little')
                result += xs[start].to_bytes(2, 'little', signed=True) + y.to_bytes(2, 'little', signed=True)
                result += runs
            else:
                result += (len(values) * 2).to_bytes(2, 'little')
                result += xs[start].to_bytes(2, 'little', signed=True) + y.to_bytes(2, 'little', signed=True)
                result += bytes(values)
            start = end + 1
    result += b'\x00\x00'
    return bytes(result)


def palette(game_path, archive):
    """→ 768 байт RGB палитры архива (8 бит на компоненту)."""
    source = PALETTES[archive]
    if source == 'U6PAL':
        raw = tools.file.read(find(game_path, 'U6PAL'))[:768]
    else:
        packed = tools.file.read(find(game_path, 'PALETTES.INT'))[source * 576 : (source + 1) * 576]
        bits = int.from_bytes(packed, 'little')
        raw = bytes((bits >> (6 * i)) & 63 for i in range(768))
    return bytes((c << 2) | (c >> 4) for c in raw)


def to_image(frame, rgb):
    (right, left, top, bottom), pixels = decode_frame(frame)
    assert TRANSPARENT not in pixels.values(), f'Index {TRANSPARENT} is used, it is reserved for transparency.'
    image = Image.new('P', (left + right + 1, top + bottom + 1), TRANSPARENT)
    image.putpalette(rgb)
    image.info['transparency'] = TRANSPARENT
    for (x, y), c in pixels.items():
        image.putpixel((x + left, y + top), c)
    return image


def check_image(image, rgb, name):
    """Палитра и прозрачность как у выгрузки (СП приводит перерисовки к палитре оригинала)."""
    assert image.mode == 'P', f'{name}: expected an indexed PNG, got {image.mode}.'
    used = {index for _, index in image.getcolors(256)}
    palette = image.getpalette()
    wrong = sorted(i for i in used if i != TRANSPARENT and palette[i * 3 : i * 3 + 3] != list(rgb[i * 3 : i * 3 + 3]))
    assert not wrong, f'{name}: palette differs from the game palette at indices {wrong[:10]}.'
    transparency = image.info.get('transparency')
    if isinstance(transparency, bytes):
        transparent = {i for i, alpha in enumerate(transparency) if alpha == 0} & used
        partial = {i for i, alpha in enumerate(transparency) if 0 < alpha < 255} & used
        assert not partial, f'{name}: semi-transparent indices {sorted(partial)}.'
    else:
        transparent = {transparency} & used if transparency is not None else set()
    assert transparent <= {TRANSPARENT}, f'{name}: transparent indices {sorted(transparent)}, expected {TRANSPARENT}.'


def from_image(image, original):
    """PNG → кадр. Сдвиг (left, top) — как у оригинального кадра."""
    assert image.mode == 'P', f'Expected an indexed PNG, got {image.mode}.'
    (_, left, top, _), _ = decode_frame(original)
    width, height = image.size
    pixels = {}
    data = image.load()
    for y in range(height):
        for x in range(width):
            if data[x, y] != TRANSPARENT:
                pixels[(x - left, y - top)] = data[x, y]
    return encode_frame((width - 1 - left, left, top, height - 1 - top), pixels)


def find(directory, name):
    """Файл без учёта регистра (в сборках встречаются intro_1.shp)."""
    for entry in os.listdir(directory):
        if entry.upper() == name.upper():
            return os.path.join(directory, entry)
    raise FileNotFoundError(os.path.join(directory, name))


def export(game_path, output_path, selection, original_path=None):
    written = []
    for archive, numbers in selection.items():
        frames = read_archive(tools.file.read(find(game_path, archive)))
        originals = read_archive(tools.file.read(find(original_path, archive))) if original_path else None
        rgb = palette(game_path, archive)
        for number in numbers if numbers is not None else range(len(frames)):
            frame = frames[number]
            if frame is None or (originals is not None and frame == originals[number]):
                continue
            path = os.path.join(output_path, archive, f'{number:03}.png')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            to_image(frame, rgb).save(path, optimize=True)
            written.append(path)
    return written


def changed_frames(png_files, original_path):
    """{путь: байты PNG} → {архив: {номер: кадр}} — только отличающиеся от оригинала."""
    result = {}
    archives = {}
    for path, data in sorted(png_files.items()):
        match = PATH.search(path.replace(os.sep, '/'))
        if not match:
            continue
        archive, number = match[1].upper(), int(match[2])
        assert archive in PALETTES, f'{path}: unknown archive {archive}, palettes are known for {sorted(PALETTES)}.'
        if archive not in archives:
            archives[archive] = read_archive(tools.file.read(find(original_path, archive)))
        frames = archives[archive]
        assert number < len(frames) and frames[number] is not None, f'{path}: no frame {number} in {archive}.'
        image = Image.open(io.BytesIO(data))
        check_image(image, palette(original_path, archive), path)
        frame = from_image(image, frames[number])
        if decode_frame(frame) != decode_frame(frames[number]):
            result.setdefault(archive, {})[number] = frame
    return result


def build(graphics_path, original_path):
    """→ {архив: сжатые байты} для архивов с перерисовками из graphics_path."""
    files = {}
    if os.path.isdir(graphics_path):
        for root, _, names in os.walk(graphics_path):
            for name in names:
                path = os.path.join(root, name)
                files[os.path.relpath(path, graphics_path)] = tools.file.read(path)
    result = {}
    for archive, changed in changed_frames(files, original_path).items():
        frames = read_archive(tools.file.read(find(original_path, archive)))
        for number, frame in changed.items():
            frames[number] = frame
        result[archive] = tools.lzw.compress(write_archive(frames))
    return result


def read_export(source):
    """Выгрузка СП (ZIP проекта или каталог) → {путь внутри выгрузки через /: байты}."""
    files = {}
    if os.path.isdir(source):
        for root, _, names in os.walk(source):
            for name in names:
                path = os.path.join(root, name)
                files[os.path.relpath(path, source).replace(os.sep, '/')] = tools.file.read(path)
    else:
        with zipfile.ZipFile(source) as archive:
            files = {info.filename: archive.read(info) for info in archive.infolist() if not info.is_dir()}
    return files


def has_frames(files):
    return any(PATH.search(path) for path in files)


def import_export(source, graphics_path, original_path):
    """Выгрузка СП (ZIP проекта или каталог) → graphics_path: только отличающиеся кадры."""
    return import_files(read_export(source), graphics_path, original_path)


def import_files(files, graphics_path, original_path, write=True):
    """Файлы выгрузки → graphics_path. Возвращает список изменений; write=False — только посчитать."""
    changes = []
    paths = {}
    for path, data in files.items():
        match = PATH.search(path.replace(os.sep, '/'))
        if match:
            target = f'{match[1].upper()}/{match[2]}.png'
            assert target not in paths, f'{path}: {target} occurs twice in the export.'
            paths[target] = path
    changed = changed_frames({target: files[path] for target, path in paths.items()}, original_path)
    keep = {f'{archive}/{number:03}.png' for archive, numbers in changed.items() for number in numbers}
    if os.path.isdir(graphics_path):
        for root, _, names in os.walk(graphics_path):
            for name in names:
                relative = os.path.relpath(os.path.join(root, name), graphics_path).replace(os.sep, '/')
                if relative not in keep:
                    if write:
                        os.remove(os.path.join(root, name))
                    changes.append(f'removed {relative}')
    for target in sorted(keep):
        path = os.path.join(graphics_path, target)
        old = tools.file.read(path) if os.path.isfile(path) else None
        if old != files[paths[target]]:
            if write:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tools.file.write(path, files[paths[target]])
            changes.append(f'{"updated" if old else "added"} {target}')
    for change in changes:
        print(change)
    print(f'{len(keep)} redrawn frames of {len(paths)} images in the export')
    return changes


def main():
    args = sys.argv[1:]
    assert args and args[0] in ('export', 'import'), __doc__
    if args[0] == 'import':
        source, graphics_path = (args[1:] + [os.path.join(tools.get_script_path(), GRAPHICS)])[:2]
        import_export(source, graphics_path, os.path.join(tools.get_script_path(), 'original'))
        return
    original_path = None
    if '--changed' in args:
        i = args.index('--changed')
        original_path = args[i + 1]
        del args[i : i + 2]
    game_path, output_path, *items = args[1:]
    if items:
        selection = {}
        for item in items:
            archive, _, numbers = item.partition(':')
            selection[archive.upper()] = [int(n) for n in numbers.split(',')] if numbers else None
    elif original_path:
        selection = dict.fromkeys(PALETTES)
    else:
        selection = TEXT_FRAMES
    for path in export(game_path, output_path, selection, original_path):
        print(path)


if __name__ == '__main__':
    main()
