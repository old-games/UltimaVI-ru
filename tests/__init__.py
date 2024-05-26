import os
import shutil
import time
import unittest

import testbox

import tools.file
import tools.lzw


class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.__script_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        super().__init__(*args, **kwargs)

    @property
    def script_path(self):
        return self.__script_path


class InstalledTestCase(unittest.TestCase):
    def setUp(self):
        configuration = {
            'cpu': {
                'cycles': 'max',
            },
            'render': {
                'scaler': 'normal2x forced',
            },
        }

        with testbox.TestBox(
            [
                '-c', 'MOUNT C: .',
                '-c', 'C:',
                'INSTALL.EXE',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            for keys in (
                'H', # Hard disk.
                'C', # Drive C:.
                '5', # VGA.
                'Y', # Mouse.
                '1', # Adlib.
                '\r', # Default port.
                'Y', # Everything is correct.
            ):
                box.send_keys(keys)
                time.sleep(0.1)

            box.wait_image('screenshots/INSTALL/install.png', bbox=(0, 16, 640, 400), timeout=2)
            self.assertTrue(os.path.isfile('CONFIG.U6'))

    def tearDown(self):
        os.remove('MAP')
        os.remove('CONFIG.U6')
        shutil.rmtree('SAVEGAME')


class ConfiguredTestCase(unittest.TestCase):
    def setUp(self):
        tools.file.write('CONFIG.U6', b'\x76\x6d\x61\x33\x38\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        tools.file.write('MAP', tools.lzw.decompress(tools.file.read('original/LZMAP')))

    def tearDown(self):
        os.remove('MAP')
        os.remove('CONFIG.U6')
        if os.path.isdir('SAVEGAME'):
            shutil.rmtree('SAVEGAME')
