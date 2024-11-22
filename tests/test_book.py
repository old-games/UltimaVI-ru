import json
import os

import tests
import tools.file
import tools.book


class TestBook(tests.TestCase):
    def testUser(self):
        expected = tools.file.read(os.path.join(self.script_path, 'original', 'BOOK.DAT'))
        book = json.loads(tools.file.read(os.path.join(self.script_path, 'unpacked', 'book.json')))

        with self.subTest(language='english'):
            self.assertEqual(tools.book.encode(book, 'english'), expected)

        with self.subTest(language='russian'):
            tools.book.encode(book, 'russian')

    # FIXME test decode, test encode
