import time
import unittest

import testbox
import tests


class TestEnd(tests.TestCase):
    #@unittest.skip('TBD')
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
            time.sleep(1000)

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
            box.wait_image('screenshots/clear.png', timeout=1)
