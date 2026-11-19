import contextlib
import io
import json
import os
import tempfile

import tests
import tools.file
import tools.sp
import tools.xlsx

ALICE = """source('CONVERSE.A')
index(1)

id(1)
name({
    'english': 'Alice',
    'russian': 'Алиса'
})

interaction:
    print({
        'english': '"Hello, $P!\\n"',
        'russian': '"Привет, $P!\\n"'
    })
    case {'russian': 'имя'}:
    print({
        'english': 'It\\'s me.',
        'russian': 'Это я.'
    })
"""

BOB = """source('CONVERSE.B')
index(2)

id(2)
name({
    'english': 'Bob',
    'russian': 'Боб'
})
"""


class TestSp(tests.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = self.directory.name
        os.mkdir(os.path.join(self.root, 'conversations'))
        self.write('Alice', ALICE)
        self.write('Bob', BOB)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, name, text):
        tools.file.write(os.path.join(self.root, 'conversations', f'{name}.txt'), text.encode('utf-8'))

    def read(self, name):
        return tools.file.read(os.path.join(self.root, 'conversations', f'{name}.txt')).decode('utf-8')

    def export(self, rows, name='export'):
        path = os.path.join(self.root, name)
        os.makedirs(path)
        manifest = {
            'revision': 'r',
            'translations': [
                {
                    'id': 249,
                    'title': 'Ultima VI Scripts',
                    'type': 'text',
                    'path': 'Scripts.xlsx',
                    'phrases': len(rows),
                    'translated': len(rows),
                }
            ],
        }
        tools.file.write(os.path.join(path, 'manifest.json'), json.dumps(manifest).encode('utf-8'))
        tools.file.write(os.path.join(path, 'Scripts.xlsx'), tools.xlsx.write('Scripts.xlsx', rows))
        return path

    def rows(self, hello='"Привет, $P!\\n"', me='Это я.', alice='Алиса'):
        return [
            ['Alice', ''],
            ['Alice', alice],
            ['"Hello, $P!\\n"', hello],
            ["It\\'s me.", me],
            ['Bob', ''],
            ['Bob', 'Боб'],
        ]

    def run_import(self, rows, name='export'):
        with contextlib.redirect_stdout(io.StringIO()):
            return tools.sp.import_export(self.export(rows, name), root=self.root)

    def testUnchanged(self):
        result = self.run_import(self.rows())
        self.assertEqual((result.changes, result.errors, result.warnings), ({}, [], []))
        self.assertEqual(self.read('Alice'), ALICE)

    def testOrder(self):
        result = self.run_import(self.rows(me="Это я, Алиса's."))
        self.assertEqual((result.changes, result.errors), ({'Alice': 1}, []))
        self.assertEqual(self.read('Alice'), ALICE.replace("'Это я.'", "'Это я, Алиса\\'s.'"))
        self.assertEqual(self.read('Bob'), BOB)

    def testEmptyName(self):
        # Стёртое имя персонажа (английский = имя файла) — реплика, а не второй заголовок.
        result = self.run_import(self.rows(alice=''))
        self.assertEqual(result.errors, [])
        self.assertIn("'russian': ''\n", self.read('Alice'))

    def testEnglishMismatch(self):
        rows = self.rows(me='Я')
        rows[3][0] = 'It is me.'
        result = self.run_import(rows)
        self.assertEqual(result.changes, {})
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(self.read('Alice'), ALICE)

    def testCount(self):
        rows = self.rows()
        del rows[3]
        result = self.run_import(rows)
        self.assertEqual(len(result.errors), 1)

    def testBadText(self):
        for text in ('«Привет»', 'Привет\\', 'При вет\xff'):
            with self.subTest(text=text):
                result = self.run_import(self.rows(hello=text), text.encode().hex())
                self.assertEqual(len(result.errors), 1, result.errors)
                self.assertEqual(self.read('Alice'), ALICE)

    def testWarnings(self):
        result = self.run_import(self.rows(hello='"Привет!\\n"'))
        self.assertEqual(result.changes, {'Alice': 1})
        self.assertEqual(len(result.warnings), 1)

    def testNewline(self):
        self.run_import(self.rows(hello='"Привет,\n$P!"'))
        self.assertIn("'russian': '\"Привет,\\n$P!\"'", self.read('Alice'))

    def testKeys(self):
        source = self.export(self.rows())
        output = os.path.join(self.root, 'keys.xlsx')
        with contextlib.redirect_stdout(io.StringIO()):
            tools.sp.keys(source, output, root=self.root)
        table = tools.xlsx.read(output, tools.file.read(output))
        self.assertEqual([row[:2] for row in table], self.rows())
        self.assertEqual(table[0][2], 'CONV:Alice')
        self.assertTrue(all(row[2].startswith('CONV:') and row[3] for row in table))
        self.assertEqual(len({row[2] for row in table}), len(table))
        # С ключами порядок не важен, лишние и недостающие фразы — предупреждения.
        keyed = [table[3], table[2], table[1], table[5], table[4]]
        keyed[0] = keyed[0][:1] + ['Это снова я.'] + keyed[0][2:]
        keyed.append(['Extra', 'Лишняя', 'CONV:Bob:ffffff', ''])
        result = self.run_import(keyed, 'keyed')
        self.assertEqual((result.changes, result.errors), ({'Alice': 1}, []))
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("'Это снова я.'", self.read('Alice'))

    def testRealConversations(self):
        conversations = tools.sp.load_conversations(os.path.join(self.script_path, 'conversations'))
        keys = [pair.key for conversation in conversations.values() for pair in conversation.pairs]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(len(key) <= 64 for key in keys))
