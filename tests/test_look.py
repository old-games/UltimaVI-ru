import json
import os

import tests
import tools.file
import tools.look
import tools.lzw


class TestLook(tests.TestCase):
    def testUser(self):
        expected = tools.file.read(os.path.join(self.script_path, 'original', 'LOOK.LZD'))
        look = json.loads(tools.file.read(os.path.join(self.script_path, 'unpacked', 'look.json')))

        with self.subTest(language='english'):
            data = tools.look.encode(look, 'english')
            self.assertEqual(tools.lzw.compress(data), expected)

        with self.subTest(language='russian'):
            tools.look.encode(look, 'russian')

    # FIXME test decode, test encode
