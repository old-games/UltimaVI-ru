import os
import tempfile

import tests
import tools.archive


class TestArchive(tests.TestCase):
    def testDecodeEncode(self):
        # FIXME test 16 bit
        with tempfile.TemporaryDirectory() as d:
            for name in ('CONVERSE.A', 'CONVERSE.B', 'PORTRAIT.A', 'PORTRAIT.B', 'PORTRAIT.Z'):
                with self.subTest(name=name):
                    path = os.path.join(self.script_path, 'original', name)
                    with open(path, 'rb') as f:
                        expected = f.read()

                    ours_path = os.path.join(d, name)
                    data = tools.archive.decode(path)
                    tools.archive.encode(data, ours_path)
                    with open(ours_path, 'rb') as f:
                        ours = f.read()

                    self.assertEqual(ours, expected)
