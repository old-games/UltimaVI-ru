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
            }
        }

        with testbox.TestBox(
            [
                '-c', 'MOUNT C: .',
                '-c', 'C:',
                '-c', 'RK211.COM /L:RUSSIAN.RK /F:8X16.RK', # FIXME `RK.COM`
                'U.EXE'
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            box.send_keys('\x1b') # Esc.
            box.wait_image('screenshots/U/menu.png', timeout=10)
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
            }
        }

        with testbox.TestBox(
            [
                '-c', 'MOUNT C: .',
                '-c', 'C:',
                '-c', 'RK211.COM /L:RUSSIAN.RK /F:8X16.RK', # FIXME `RK.COM`
                'U.EXE'
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            box.send_keys('\x1b') # Esc.
            box.wait_image('screenshots/U/menu.png', timeout=10)
            box.send_keys('▾')
            box.wait_image('screenshots/U/new.png', timeout=1)
            time.sleep(0.1)
            box.send_keys('\r')
            box.wait_image('screenshots/U/name.png', timeout=10)
            box.send_keys('Vladimir\r')
            time.sleep(0.1)
            box.send_keys('M')
            time.sleep(0.1)
            box.send_keys('C')
            box.wait_image('screenshots/U/create.png', timeout=10)
            box.send_keys('\r')
            box.wait_image('screenshots/U/scroll.png', timeout=10)
            box.send_keys('\r')
            time.sleep(0.1)
            box.send_keys('\r')
            box.wait_image('screenshots/U/inside.png', timeout=5)
            box.send_keys('\r')
            time.sleep(0.1)
            box.send_keys('\r')
            for _ in range(7):
                time.sleep(0.5)
                box.send_keys('A')

            # TODO Five spaces one Esc

            print('Go')
            time.sleep(1000)
