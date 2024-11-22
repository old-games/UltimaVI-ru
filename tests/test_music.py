import os

import tests
import tools.file
import tools.music


class TestMusic(tests.TestCase):
    def test_read(self):
        for name in ('BOOTUP.M', 'BRIT.M', 'CREATE.M', 'DUNGEON.M', 'END.M', 'ENGAGE.M', 'FOREST.M', 'GARGOYLE.M', 'HORNPIPE.M', 'INTRO.M', 'STONES.M', 'ULTIMA.M'):
            with self.subTest(name=name):
                path = os.path.join(self.script_path, 'unpacked', name)
                tools.music.decode(tools.file.read(path))
