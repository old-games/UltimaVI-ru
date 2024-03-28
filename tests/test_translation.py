import collections
import json

import tests


class TestTranslation(tests.TestCase):
    @staticmethod
    def readNullTerminatedString(d, i):
        s = ''
        while d[i]:
            s += d[i:i+1].decode('ascii')
            i += 1
        return s

    def testTranslation(self):
        with open('patches/translation.json') as f:
            t = json.loads(f.read())

        by_source = collections.defaultdict(list)
        for index, i in enumerate(t):
            with self.subTest(index=index):
                self.assertEqual(set(i.keys()), {'source', 'offset', 'english', 'russian'})
                self.assertIn(i['source'], {'GAME.EXE', 'END.EXE', 'INSTALL.EXE', 'U.EXE', 'ULTIMA6.EXE'}, f'Invalid source: "{i["source"]}".')
                self.assertIsInstance(i['offset'], int)
                by_source[i['source']].append(i)

        for s, ii in by_source.items():
            with self.subTest(name=s):
                with open(f'unpacked/{s}', 'rb') as f:
                    x = f.read()
                for index, i in enumerate(ii):
                    with self.subTest(index=index):
                        text = self.readNullTerminatedString(x, i['offset'])
                        self.assertEqual(text, i['english'], f'English text could not be found at offset {i["offset"]}: "{i["english"]}".')

    def testNotStrings(self):
        with open('patches/not-strings.json') as f:
            ns = json.loads(f.read())

        by_source = collections.defaultdict(list)
        for index, i in enumerate(ns):
            with self.subTest(index=index):
                self.assertEqual(set(i.keys()), {'source', 'offset', 'text'})
                self.assertIn(i['source'], {'GAME.EXE', 'END.EXE', 'INSTALL.EXE', 'U.EXE', 'ULTIMA6.EXE'}, f'Invalid source: "{i["source"]}".')
                self.assertIsInstance(i['offset'], int)
                by_source[i['source']].append(i)

        for s, ii in by_source.items():
            with self.subTest(name=s):
                with open(f'unpacked/{s}', 'rb') as f:
                    x = f.read()
                for index, i in enumerate(ii):
                    with self.subTest(index=index):
                        text = self.readNullTerminatedString(x, i['offset'])
                        self.assertEqual(text, i['text'], f'Text could not be found at offset {i["offset"]}: "{i["text"]}".')

    def testReferences(self):
        # FIXME
        with open('patches/references.json') as f:
            r = json.loads(f.read())

    def testBadReferences(self):
        # FIXME
        with open('patches/bad-references.json') as f:
            br = json.loads(f.read())
