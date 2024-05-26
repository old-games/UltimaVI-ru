import shutil
import time
import unittest

import testbox
import tests


class TestGame(tests.ConfiguredTestCase):
    #@unittest.skip('TBD')
    def testGame(self):
        # FIXME игре нужен созданный персонаж
        shutil.copytree('tests/testgame', 'SAVEGAME')

        configuration = {
            'cpu': {
                'cycles': 'max',
            },
            'render': {
                'scaler': 'normal5x',
            },
        }

        with testbox.TestBox(
            [
                '-c', 'MOUNT C: .',
                '-c', 'C:',
                '-c', 'RK.COM /L:RUSSIAN.RK /F:8X16.RK',
                'GAME.EXE',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            time.sleep(1000)
