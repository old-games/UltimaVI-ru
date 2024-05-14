import os
import time
import unittest

import testbox
import tests


class TestU(tests.InstalledTestCase):
    def testExitWithDriver(self):
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
                '-c', 'RK211.COM /L:RUSSIAN.RK /F:8X16.RK', # FIXME `RK.COM`
                'U.EXE',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            box.send_keys('\x1b') # Esc.
            box.wait_image('screenshots/U/menu.png', timeout=6)
            box.send_keys('\x11') # Ctrl+Q.
            box.wait_image('screenshots/U/exit.png', timeout=1)

    @unittest.skip('TBD')
    def testU(self):
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
                'U.EXE',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            time.sleep(1000)
