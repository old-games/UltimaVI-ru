"""Шрифты игры (tools/U6.CH.txt, tools/U6.SET.txt) ⇄ BDF для банка шрифтов «Системы Переводчик».

python3 -m tools.bdf export <U6.CH.txt|U6.SET.txt> <файл.bdf> <название>
python3 -m tools.bdf import <файл.bdf> <U6.CH.txt|U6.SET.txt>
    Знаки 0x20–0xFF из BDF (по символу Unicode → CP866) записываются в текстовый файл шрифта, из которого
    собирается игра (tools.symbols). Знаков, которых нет в BDF, и 0x00–0x1F, 0x100+ импорт не трогает; символы
    BDF вне CP866 (например «») пропускает с предупреждением. Ширина: U6.CH — ровно 8, U6.SET — от 1 до ширины
    ячейки файла; точки вне ширины знака или вне 8 строк (7 над базовой линией, 1 под) — ошибка.

Знаки 0x20–0xFF — раскладка CP866 (русские буквы, псевдографика, Ё/ё на F0/F1), в BDF — их символы Unicode.
Не выгружаются: 0x00–0x1F (значки игры, не текст) и в U6.CH знаки 0x100+ (вытесненная верхняя половина
оригинального шрифта: значки, руны). Высота 8 точек, базовая линия над нижней строкой (у p, q, y хвост в строке 7).
U6.CH — моноширинный 8×8, U6.SET — ширина у каждого знака своя (как в файле, вместе с промежутком справа).
"""

import os
import sys

BLOCKS = {(0, 0): ' ', (1, 0): '▀', (0, 1): '▄', (1, 1): '█'}

HAS_PIXEL = ('▀█', '█▄')
HEIGHT = 8
DESCENT = 1


def read_glyphs(path):
    """→ {код: (ширина, [8 строк по ширине из 0/1])}"""
    with open(path) as f:
        lines = f.read().splitlines()
    assert len(lines) % 5 == 0
    size = max(map(len, lines)) // 0x10
    glyphs = {}
    for row in range(len(lines) // 5):
        base = int(lines[row * 5], 16)
        rows = lines[row * 5 + 1 : row * 5 + 5]
        for column in range(0x10):
            cells = [line[column * size : (column + 1) * size] for line in rows]
            width = cells[0].index('.') if '.' in cells[0] else len(cells[0])
            bitmap = [[int(cells[y // 2][x] in HAS_PIXEL[y % 2]) for x in range(width)] for y in range(HEIGHT)]
            glyphs[base + column] = width, bitmap
    return glyphs


def to_bdf(glyphs, name):
    chars = []
    for code, (width, bitmap) in sorted(glyphs.items()):
        if not 0x20 <= code <= 0xFF:
            continue
        char = bytes([code]).decode('cp866')
        nbytes = max(1, (width + 7) // 8)
        rows = []
        for line in bitmap:
            value = 0
            for x, bit in enumerate(line):
                value |= bit << (nbytes * 8 - 1 - x)
            rows.append(f'{value:0{nbytes * 2}X}')
        chars.append(
            [
                f'STARTCHAR U+{ord(char):04X}',
                f'ENCODING {ord(char)}',
                f'SWIDTH {width * 1000 // HEIGHT} 0',
                f'DWIDTH {width} 0',
                f'BBX {max(width, 1)} {HEIGHT} 0 {-DESCENT}',
                'BITMAP',
                *rows,
                'ENDCHAR',
            ]
        )
    max_width = max(width for width, _ in glyphs.values())
    header = [
        'STARTFONT 2.1',
        f'FONT {name}',
        f'SIZE {HEIGHT} 75 75',
        f'FONTBOUNDINGBOX {max(max_width, 8)} {HEIGHT} 0 {-DESCENT}',
        'STARTPROPERTIES 4',
        f'FONT_ASCENT {HEIGHT - DESCENT}',
        f'FONT_DESCENT {DESCENT}',
        'CHARSET_REGISTRY "ISO10646"',
        'CHARSET_ENCODING "1"',
        'ENDPROPERTIES',
        f'CHARS {len(chars)}',
    ]
    return '\n'.join(header + [line for char in chars for line in char] + ['ENDFONT']) + '\n'


def read_bdf(text):
    """→ {символ: (ширина, [8 строк по ширине из 0/1])} в сетке шрифта игры."""
    glyphs = {}
    char = None
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        key = fields[0]
        if key == 'STARTCHAR':
            char = {'name': line[len('STARTCHAR') :].strip(), 'rows': None}
        elif char is None:
            continue
        elif key == 'ENCODING':
            char['code'] = int(fields[1])
        elif key == 'DWIDTH':
            char['width'] = int(fields[1])
        elif key == 'BBX':
            char['bbx'] = tuple(map(int, fields[1:5]))
        elif key == 'BITMAP':
            char['rows'] = []
        elif key == 'ENDCHAR':
            code, width = char['code'], char['width']
            w, h, x0, y0 = char['bbx']
            assert len(char['rows']) == h, f'Line {number}: {char["name"]}: {len(char["rows"])} rows, BBX says {h}.'
            bitmap = [[0] * width for _ in range(HEIGHT)]
            for i, hexs in enumerate(char['rows']):
                value, bits = int(hexs, 16), len(hexs) * 4
                y = y0 + h - 1 - i  # от базовой линии вверх
                for x in range(w):
                    if value >> (bits - 1 - x) & 1:
                        row, column = HEIGHT - DESCENT - 1 - y, x0 + x
                        assert 0 <= row < HEIGHT and 0 <= column < width, (
                            f'{chr(code) if code >= 0 else char["name"]!r}: pixel ({column}, {row}) is outside '
                            f'{width}×{HEIGHT} (baseline above the last row).'
                        )
                        bitmap[row][column] = 1
            if code >= 0:
                glyphs[chr(code)] = width, bitmap
            char = None
        elif char['rows'] is not None:
            char['rows'].append(fields[0])
    return glyphs


def import_bdf(text, path):
    """Записывает знаки BDF в текстовый файл шрифта. → (заменено, пропущено вне CP866)"""
    with open(path) as f:
        lines = f.read().splitlines()
    size = max(map(len, lines)) // 0x10
    fixed = os.path.basename(path).upper().startswith('U6.CH')
    codes = {}
    for code in range(0x20, 0x100):
        codes[bytes([code]).decode('cp866')] = code
    glyphs = read_bdf(text)
    skipped = sorted(char for char in glyphs if char not in codes)
    rows = {int(lines[row * 5], 16): row for row in range(len(lines) // 5)}
    changed = 0
    for char, (width, bitmap) in glyphs.items():
        if char not in codes:
            continue
        code = codes[char]
        if fixed:
            assert width == 8, f'{char!r}: width {width}, U6.CH glyphs are exactly 8 wide.'
        else:
            assert 1 <= width <= size, f'{char!r}: width {width}, the cell allows 1..{size}.'
        row = rows[code & ~0xF] * 5
        column = code & 0xF
        for i in range(4):
            cell = ''.join(BLOCKS[bitmap[i * 2][x], bitmap[i * 2 + 1][x]] for x in range(width))
            cell += '.' * (size - width)
            line = lines[row + 1 + i].ljust(size * 0x10)
            new = line[: column * size] + cell + line[(column + 1) * size :]
            changed += new != line
            lines[row + 1 + i] = new
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return changed, skipped


def main():
    command, *args = sys.argv[1:]
    if command == 'export':
        input_path, output_path, name = args
        with open(output_path, 'w') as f:
            f.write(to_bdf(read_glyphs(input_path), name))
    elif command == 'import':
        bdf_path, txt_path = args
        with open(bdf_path, encoding='utf-8', errors='replace') as f:
            changed, skipped = import_bdf(f.read(), txt_path)
        print(f'{txt_path}: {changed} lines changed')
        if skipped:
            print(f'Not in CP866, skipped: {" ".join(skipped)}')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
