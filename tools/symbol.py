import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont


def make_image(input_path, output_path, symbol_width):
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
                    if lines[row][column] in pixels:
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
            ), fill='white')
            for column in range(0, len(lines[row+1]), symbol_width):
                draw.text((column*factor+1, (row//5*8+row//5+1)*factor-2), f'{code+column//symbol_width:02X}', fill='red', anchor='ls', font=font)

    image.save(output_path)
