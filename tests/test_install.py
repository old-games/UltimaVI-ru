import time

import testbox
import tests


class TestInstall(tests.TestCase):
    def testInstall(self):
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
                '-c', 'RK.COM /L:RUSSIAN.RK /F:8X16.RK',
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
                '2', # Don't create character.
            ):
                # FIXME save screenshots and pack as artifacts.
                box.send_keys(keys)
                time.sleep(0.1)
            box.wait_image('screenshots/INSTALL/install.png', bbox=(0, 16, 640, 400), timeout=1)

            with open('CONFIG.U6', 'rb') as f:
                self.assertEqual(f.read(), b'\x76\x6d\x61\x33\x38\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
