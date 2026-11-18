import os
import shutil
import tempfile

import tests
import tools.bdf


class TestBdf(tests.TestCase):
    def testRoundTrip(self):
        # Выгрузка в BDF и импорт обратно не меняют текстовый файл шрифта.
        for name in ('U6.CH.txt', 'U6.SET.txt'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                source = os.path.join(self.script_path, 'tools', name)
                path = os.path.join(d, name)
                shutil.copy(source, path)
                bdf = tools.bdf.to_bdf(tools.bdf.read_glyphs(source), 'test')
                self.assertEqual(tools.bdf.import_bdf(bdf, path), (0, []))
                with open(path) as a, open(source) as b:
                    self.assertEqual(a.read(), b.read())

    def testGlyph(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'U6.CH.txt')
            shutil.copy(os.path.join(self.script_path, 'tools', 'U6.CH.txt'), path)
            glyphs = tools.bdf.read_glyphs(path)
            glyphs[0x86] = 8, [[1] * 8] * 7 + [[0] * 8]  # Ж
            tools.bdf.import_bdf(tools.bdf.to_bdf(glyphs, 'test'), path)
            self.assertEqual(tools.bdf.read_glyphs(path)[0x86], glyphs[0x86])
            glyphs[0x41] = 9, [[1] * 9] * 8
            with self.assertRaises(AssertionError):
                tools.bdf.import_bdf(tools.bdf.to_bdf(glyphs, 'test'), path)
