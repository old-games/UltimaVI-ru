import io
import os

from PIL import Image

import tests
import tools.file
import tools.lzw
import tools.shapes

ARCHIVES = (
    'BLOCKS.SHP', 'END.SHP', 'GYPSY.SHP', 'INTRO_1.SHP', 'INTRO_2.SHP', 'INTRO_3.SHP',
    'INTRO.SHP', 'MAINMENU.SHP', 'MONTAGE.SHP', 'TITLES.SHP', 'VELLUM1.SHP', 'WOODS.SHP',
)


class TestShapes(tests.TestCase):
    def testArchives(self):
        for name in ARCHIVES:
            with self.subTest(name=name):
                data = tools.file.read(os.path.join(self.script_path, 'original', name))
                frames = tools.shapes.read_archive(data)
                self.assertEqual(tools.shapes.write_archive(frames), tools.lzw.decompress(data))

    def testFrames(self):
        # Серии сжимаются не так, как у Origin, поэтому сравниваются пиксели, а не байты.
        for name in ARCHIVES:
            original = os.path.join(self.script_path, 'original')
            frames = tools.shapes.read_archive(tools.file.read(os.path.join(original, name)))
            for number, frame in enumerate(frames):
                with self.subTest(name=name, number=number):
                    decoded = tools.shapes.decode_frame(frame)
                    self.assertEqual(tools.shapes.decode_frame(tools.shapes.encode_frame(*decoded)), decoded)
                    self.assertNotIn(tools.shapes.TRANSPARENT, decoded[1].values())

    def testImages(self):
        original = os.path.join(self.script_path, 'original')
        for name in tools.shapes.PALETTES:
            rgb = tools.shapes.palette(original, name)
            frames = tools.shapes.read_archive(tools.file.read(os.path.join(original, name)))
            for number in tools.shapes.TEXT_FRAMES[name]:
                with self.subTest(name=name, number=number):
                    buffer = io.BytesIO()
                    tools.shapes.to_image(frames[number], rgb).save(buffer, 'PNG')
                    image = Image.open(io.BytesIO(buffer.getvalue()))
                    self.assertEqual(
                        tools.shapes.decode_frame(tools.shapes.from_image(image, frames[number])),
                        tools.shapes.decode_frame(frames[number]),
                    )

    def testGraphics(self):
        # Перерисовки из graphics/ попадают в собранные архивы, остальные кадры — байты оригинала.
        original = os.path.join(self.script_path, 'original')
        graphics = os.path.join(self.script_path, tools.shapes.GRAPHICS)
        built = tools.shapes.build(graphics, original)
        for archive, data in built.items():
            frames = tools.shapes.read_archive(data)
            originals = tools.shapes.read_archive(tools.file.read(os.path.join(original, archive)))
            rgb = tools.shapes.palette(original, archive)
            for number, (frame, source) in enumerate(zip(frames, originals)):
                with self.subTest(archive=archive, number=number):
                    path = os.path.join(graphics, archive, f'{number:03}.png')
                    if os.path.isfile(path):
                        image = Image.open(path)
                        tools.shapes.check_image(image, rgb, path)
                        self.assertEqual(tools.shapes.decode_frame(frame), tools.shapes.decode_frame(tools.shapes.from_image(image, source)))
                    else:
                        self.assertEqual(frame, source)
