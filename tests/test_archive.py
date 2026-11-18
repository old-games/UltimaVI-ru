import os

import tests
import tools.archive
import tools.file


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
