import collections
import os

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont


def make_image(input_path, output_path, symbol_width):
    # FIXME auto-guess symbol_width
    size = 15
    factor = size+1
    with open(input_path) as f:
        lines = f.read().splitlines()
    assert len(lines) % 5 == 0
    width = max(map(len, lines))
    new_width = width*factor-1
    height = len(lines)*2 - len(lines) // 5
    new_height = height*factor-1
    image = PIL.Image.new('RGBA', (new_width, new_height), (255, 255, 255, 0))
    draw = PIL.ImageDraw.Draw(image)
    font = PIL.ImageFont.truetype('tools/ModernDOS8x8.ttf', size*2)

    for row in range(len(lines)):
        if row % 5:
            for column in range(len(lines[row])):
                for shift, pixels in enumerate(('█▀', '█▄')):
                    if lines[row][column] == '.':
                        color = '#ffe0e0'
                    elif lines[row][column] in pixels:
                        color = 'black'
                    else:
                        color = 'white'

                    draw.rectangle((
                        column*factor,
                        ((row//5*4+(row-1)%5)*2+row//5+shift+1)*factor,
                        (column+1)*factor-2,
                        ((row//5*4+(row-1)%5)*2+row//5+shift+2)*factor-2
                    ), fill=color)

        else:
            code = int(lines[row], 16)
            draw.rectangle((
                0,
                (row//5*8+row//5)*factor,
                new_width-1,
                (row//5*8+row//5+1)*factor-2,
            ), fill='#ffc0c0')
            for column in range(0, len(lines[row+1]), symbol_width):
                draw.text((column*factor+1, (row//5*8+row//5+1)*factor-2), f'{code+column//symbol_width:02X}', fill='red', anchor='ls', font=font)

    image.save(output_path)


def read_image(input_path, output_path):
    columns = 0x10
    size = 15
    factor = size+1

    def get_colors(image):
        colors = collections.Counter()
        pixels = image.load()
        for x in range(image.width):
            for y in range(image.height):
                colors[pixels[(x, y)]] += 1
        return colors

    image = PIL.Image.open(input_path)
    assert (image.width + 1) % factor == 0
    assert (image.height + 1) % factor == 0
    width = (image.width + 1) // factor
    height = (image.height + 1) // factor
    assert width % columns == 0
    assert height % 9 == 0
    symbol_width = width // columns
    rows = height // 9
    row_height = 9 * factor

    colors = [[None]*symbol_width*columns for row in range(rows*8)]
    for row in range(rows):
        row_image = image.crop((0, row_height*row+factor, image.width, row_height*(row+1)-1))
        for column in range(columns):
            symbol = row_image.crop((symbol_width*factor*column, 0, symbol_width*factor*(column+1) - 1, row_image.height))
            for x in range(symbol_width):
                for y in range(8):
                    pixel = symbol.crop((x*factor, y*factor, (x+1)*factor-1, (y+1)*factor-1))
                    (color, _), = get_colors(pixel).most_common(1)
                    color = color[:3]
                    color_names = {
                        (0, 0, 0): 'black',
                        (255, 255, 255): 'white',
                        (255, 224, 224): 'pink'
                    }
                    assert color in color_names
                    colors[row*8+y][column*symbol_width+x] = color_names[color]

    with open(output_path, 'w') as f:
        for row in range(rows):
            rows_data = [['.']*symbol_width*columns for _ in range(4)]
            for column in range(columns):
                widths = set()
                for y in range(8):
                    for x in range(symbol_width):
                        if colors[row*8+y][column*symbol_width+x] == 'pink':
                            widths.add(x)
                            break
                    else:
                        widths.add(symbol_width)
                assert len(widths) == 1
                width, = widths

                for y in range(8):
                    for x in range(width):
                        if colors[row*8+y][column*symbol_width+x] == 'black':
                            if y % 2 == 0:
                                rows_data[y//2][column*symbol_width+x] = '▀'
                            elif rows_data[y//2][column*symbol_width+x] in ' .':
                                rows_data[y//2][column*symbol_width+x] = '▄'
                            else:
                                rows_data[y//2][column*symbol_width+x] = '█'
                        else:
                            if y % 2 == 0:
                                rows_data[y//2][column*symbol_width+x] = ' '

            print(f'{row*0x10:02X}', file=f)
            for row_data in rows_data:
                print(''.join(row_data), file=f)


def encode(input_path, output_path):
    columns = 0x10
    extension = os.path.splitext(output_path)[1]
    assert extension in ('.SET', '.CH')
    with open(input_path, 'r') as f:
        lines = f.read().splitlines()
    assert len(lines) % 5 == 0
    rows = len(lines) // 5
    widths = set(map(len, lines))
    widths.discard(2)
    widths.discard(3)
    assert len(widths) == 1, widths
    width, = widths
    assert width % 0x10 == 0
    symbol_size = width // 0x10

    symbols = []
    symbol_width = []

    for row in range(rows):
        row_data = lines[row*5+1:row*5+5]
        for column in range(columns):
            symbol_data = [line[column*symbol_size:column*symbol_size+symbol_size] for line in row_data]
            widths = set()
            for line in symbol_data:
                if '.' in line:
                    widths.add(line.index('.'))
                else:
                    widths.add(len(line))
            assert len(widths) == 1
            width, = widths
            assert extension == '.SET' or width == 8
            symbol_data = [line[:width] for line in symbol_data]
            has_pixel = ('▀█', '█▄')

            data = bytearray()
            if extension == '.CH':
                for y in range(8):
                    b = 0
                    for x in range(width):
                        if symbol_data[y//2][width-1-x] in has_pixel[y%2]:
                            b |= 1 << x
                    data.append(b)
            else:
                for y in range(8):
                    for x in range(width):
                        if symbol_data[y//2][x] in has_pixel[y%2]:
                            b = 0x0f
                        else:
                            b = 0
                        data.append(b)

            symbols.append(data)
            symbol_width.append(width)

    with open(output_path, 'wb') as f:
        if extension == '.CH':
            f.write(b''.join(symbols))

        else:
            f.write(b'\x08\x00\x0f\x00') # TODO looks like character dimensions
            f.write(b''.join((w.to_bytes(1, 'little') for w in symbol_width)))
            offset = 0x304
            for s in symbols:
                f.write((offset & 0xff).to_bytes(1, 'little'))
                offset += len(s)
            offset = 0x304
            for s in symbols:
                f.write(((offset >> 8) & 0xff).to_bytes(1, 'little'))
                offset += len(s)
            for s in symbols:
                f.write(s)

"""

import os
import sys

import tools


output_directory = sys.argv[1] if len(sys.argv) == 2 else os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open(tools.get_path('U6.CH'), 'rb') as f:
    d = f.read()

with open(tools.get_path('U6.SET'), 'rb') as f:
    s = bytearray(f.read())

with open('tools/cp866-8x8', 'rb') as f:
    e = f.read()

with open('tools/atari-st-8x8', 'rb') as f:
    g = f.read()

combined_font = d[:1024] + g[1536:1920] + e[1408:1792] + g[1920:] + g[1576:1584] + bytes((x >> 1 for x in g[1096:1104])) + e[1936:] + d[1024:]

os.chdir(output_directory)
with open('U6.CH', 'wb') as f:
    f.write(combined_font)

assert s[:4] == b'\x08\x00\x0f\x00' # Looks like character dimensions?

symbols_data = []
for i, (lo, hi, size) in enumerate(zip(s[0x104:0x204], s[0x204:0x304], s[4:0x104])):
    offset = hi*0x100+lo
    end = offset + size*8
    symbols_data.append(s[offset:end])

s = s[:0x304]

symbols = [
#    *range(0x20),
    *range(0x80, 0x100),
]
for symbol in symbols:
    data = combined_font[symbol*8:symbol*8+8]
    left = 7
    right = 0
    if 0xb0 <= symbol < 0xe0:
        left = 0
        right = 7
        start = 0
        width = 8
    else:
        for i in range(8):
            r = data[i]
            for k in range(8):
                if r & 1 << 7-k:
                    left = min(left, k)
                    right = max(right, k)
        start = 1
        width = 1 + max(0, right-left+1)
    y = bytearray([0]*width*8)
    for row in range(8):
        for col in range(start, width):
            k = left + col - start
            r = data[row]
            if r & 1 << 7-k:
                y[row*width+col] = 0x0f
    symbols_data[symbol] = y

for i, data in enumerate(symbols_data):
    offset = len(s)
    assert len(data) % 8 == 0
    width = len(data) // 8
    s[4+i] = width
    s[0x104+i] = offset & 0xff
    s[0x204+i] = offset >> 8
    s += data

with open('U6.SET', 'wb') as f:
    f.write(s)

# TODO also patch keyboard driver :)

"""


"""

import os
import sys


ext = os.path.splitext(sys.argv[1])[1]
if ext == '.CH':
    with open(sys.argv[1], 'rb') as f:
        x = f.read()

    width = 9
    result = []
    for r in range(len(x) // 128):
        result.append([f'{r*0x10:02X}'])
        for k in range(4):
            result.append(['.']*width*16)

    for i in range(len(x) // 128):
        for k in range(8):
            for j in range(16):
                for l in range(8):
                    c = i * 16 + j
                    C = x[c*8+k] & 1 << 7-l
                    if C:
                        r = result[1+k//2+i*5][j*width+l]
                        if k % 2 == 0:
                            result[1+k//2+i*5][j*width+l] = '▀'
                        elif r == ' ':
                            result[1+k//2+i*5][j*width+l] = '▄'
                        else:
                            result[1+k//2+i*5][j*width+l] = '█'
                    elif result[1+k//2+i*5][j*width+l] == '.':
                        result[1+k//2+i*5][j*width+l] = ' '

    for l in result:
        print(''.join(l))

elif ext == '.SET':
    with open(sys.argv[1], 'rb') as f:
        s = f.read()

    width = max(max(s[4:0x104]), 10) + 1
    result = []
    for r in range(16):
        result.append([f'{r*0x10:02X}'])
        for k in range(4):
            result.append(['.']*width*16)

    for i, (lo, hi, size) in enumerate(zip(s[0x104:0x204], s[0x204:0x304], s[4:0x104])):
        offset = hi*0x100+lo
        assert offset >= 0x304
        end = offset + size*8

        for j in range(8):
            for k in range(size):
                # k == 0 это отступ, справа отступа нет.
                c = s[offset+j*size+k]
                assert c in (0, 15)
                if c:
                    r = result[1+j//2+i//16*5][i%16*width+k]
                    if j % 2 == 0:
                        result[1+j//2+i//16*5][i%16*width+k] = '▀'
                    elif r == ' ':
                        result[1+j//2+i//16*5][i%16*width+k] = '▄'
                    else:
                        result[1+j//2+i//16*5][i%16*width+k] = '█'
                elif result[1+j//2+i//16*5][i%16*width+k] == '.':
                    result[1+j//2+i//16*5][i%16*width+k] = ' '

    for l in result:
        print(''.join(l))

"""
