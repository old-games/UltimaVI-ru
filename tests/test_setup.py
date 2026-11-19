import hashlib
import os
import shutil
import tempfile

import tests
import tools.install

# Файлы, которые пишет INSTALL.EXE (жёсткий диск, VGA/MCGA, мышь, AdLib 388) поверх original/: снято в DOSBox.
INSTALL_DIGEST = '17dfd726fa9facaebf57efb4410a661531f2e4aed6aebd3f39f79fcf9a3732f3'


def digest(directory):
    savegame = os.path.join(directory, 'SAVEGAME')
    names = ['MAP', 'U6.8', 'CONFIG.U6'] + [f'SAVEGAME/{name}' for name in sorted(os.listdir(savegame))]
    result = hashlib.sha256()
    for name in names:
        with open(os.path.join(directory, name), 'rb') as f:
            result.update(name.encode() + b'\0' + f.read())
    return len(names), result.hexdigest()


class TestSetup(tests.TestCase):
    def install(self, **kwargs):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        shutil.copytree(os.path.join(self.script_path, 'original'), directory, dirs_exist_ok=True)
        tools.install.install(directory, **kwargs)
        return directory

    def testLikeInstallExe(self):
        self.assertEqual(digest(self.install()), (73, INSTALL_DIGEST))

    def testAvatar(self):
        directory = self.install(launcher=True, avatar=True)
        with open(os.path.join(directory, 'SAVEGAME', 'OBJLIST'), 'rb') as f:
            objlist = f.read()
        name = objlist[tools.install.NAME : tools.install.NAME + tools.install.NAME_SIZE]
        self.assertEqual(name.rstrip(b'\0').decode('cp866'), tools.install.AVATAR_NAME)
        for offset, (_, value) in tools.install.AVATAR.items():
            self.assertEqual(objlist[offset], value)
        for name in (tools.install.LAUNCHER, *tools.install.KEYBOARD_FILES):
            self.assertTrue(os.path.isfile(os.path.join(directory, name)))
