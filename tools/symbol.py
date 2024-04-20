import collections

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
