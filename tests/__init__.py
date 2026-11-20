import os
import shutil
import time
import unittest

import testbox


class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.__script_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        super().__init__(*args, **kwargs)

    @property
    def script_path(self):
        return self.__script_path


class InstalledTestCase(unittest.TestCase):
    def setUp(self):
        # Сборка уже установлена (tools/install.py), а INSTALL.EXE при существующем CONFIG.U6 сначала спрашивает,
        # что делать с текущим персонажем. Тесты проверяют чистую установку — готовая убирается.
        if os.path.isfile('CONFIG.U6'):
            os.remove('CONFIG.U6')
        shutil.rmtree('SAVEGAME', ignore_errors=True)

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

            # Установка пишет карту и сохранение — на занятой машине CI за 1 с не успевала (тест U, 19.11).
            box.wait_image('screenshots/INSTALL/install.png', bbox=(0, 16, 640, 400), timeout=10)
            self.assertTrue(os.path.isfile('CONFIG.U6'))

    def tearDown(self):
        os.remove('MAP')
        os.remove('CONFIG.U6')
        shutil.rmtree('SAVEGAME')
