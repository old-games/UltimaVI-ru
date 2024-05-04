import os

import tests
import tools.archive
import tools.file
import tools.lzw


class TestArchive(tests.TestCase):
    def testConversationsAndPortraits(self):
        for name in ('CONVERSE.A', 'CONVERSE.B', 'PORTRAIT.A', 'PORTRAIT.B', 'PORTRAIT.Z'):
            with self.subTest(name=name):
                path = os.path.join(self.script_path, 'original', name)
                expected = tools.file.read(path)

                data = tools.archive.decode(expected)
                ours = tools.archive.encode(data)

                self.assertEqual(ours, expected)


    def testBook(self):
        # FIXME test write
        path = os.path.join(self.script_path, 'original', 'BOOK.DAT')
        expected = tools.file.read(path)

        data = tools.archive.decode(expected, bits=16)
        for item in data:
            # FIXME
            assert item is not None


    def testShapes(self):
        # FIXME test write
        for name in (
            'BLOCKS.SHP', 'END.SHP', 'GYPSY.SHP', 'INTRO_1.SHP', 'INTRO_2.SHP', 'INTRO_3.SHP',
            'INTRO.SHP', 'MAINMENU.SHP', 'MONTAGE.SHP', 'TITLES.SHP', 'VELLUM1.SHP', 'WOODS.SHP'
        ):
            with self.subTest(name=name):
                path = os.path.join(self.script_path, 'original', name)
                expected = tools.lzw.decompress(tools.file.read(path))

                size = int.from_bytes(expected[:4], 'little')
                self.assertEqual(len(expected), size)

                data = tools.archive.decode(expected[4:], ordered=False)
                for item in data:
                    assert item is not None
