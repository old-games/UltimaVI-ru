import time

import testbox
import tests


class TestGame(tests.TestCase):
    def testGame(self):
        with open('CONFIG.U6', 'wb') as f:
            f.write(b'\x76\x6d\x61\x33\x38\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

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
