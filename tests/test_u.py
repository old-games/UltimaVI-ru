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
                '-c', 'RK.COM /L:RUSSIAN.RK /F:8X16.RK',
                'U.EXE',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            box.send_keys('\x1b') # Esc.
            time.sleep(0.1)
            box.wait_image('screenshots/U/menu.png', timeout=5)
            # FIXME
            box.send_keys('\x11') # Ctrl+Q.
            #time.sleep(1000) FIXME

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
