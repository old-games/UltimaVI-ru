import time
import unittest

import testbox
import tests


class TestEnd(tests.TestCase):
    def testEnd(self):
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
                '-c', 'END.EXE vma388 10 11 29',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            box.wait_image('screenshots/END/one.png', bbox=(0, 0, 320, 120), timeout=15)
            box.send_keys(' ')
            box.wait_image('screenshots/END/two.png', bbox=(0, 0, 320, 120), timeout=1)
            box.send_keys(' ')
            box.wait_image('screenshots/END/three.png', bbox=(0, 0, 320, 120), timeout=10)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            box.wait_image('screenshots/END/four.png', bbox=(0, 90, 320, 120), timeout=1)
            box.wait_image('screenshots/END/four.png', bbox=(152, 30, 170, 54), timeout=15)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            box.wait_image('screenshots/END/five.png', bbox=(0, 90, 320, 120), timeout=15)
            box.send_keys(' ')
            box.wait_image('screenshots/END/six.png', bbox=(0, 90, 320, 120), timeout=5)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            box.wait_image('screenshots/END/seven.png', bbox=(0, 90, 320, 120), timeout=1)
            box.send_keys(' ')
            box.wait_image('screenshots/END/eight.png', bbox=(140, 30, 185, 55), timeout=10)
            box.send_keys(' ')
            time.sleep(0.2)
            box.send_keys(' ')
            box.wait_image('screenshots/END/nine.png', timeout=15)
            box.send_keys(' ')
            time.sleep(5)
            box.wait_image('screenshots/END/ten.png', bbox=(0, 0, 320, 72), timeout=1)
            box.send_keys(' ')
            box.wait_image('screenshots/END/clear.png', timeout=1)

    def testEndNoArguments(self):
        with open('CONFIG.U6', 'wb') as f:
            f.write(b'\x76\x6d\x61\x33\x38\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

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
                '-c', 'DEBUG END.EXE',
                '-c', 'CLS',
            ],
            configuration,
            timeout_error=AssertionError,
        ) as box:
            box.wait_image('screenshots/END/clear.png', timeout=1)
