import tests


class TestInstall(tests.InstalledTestCase):
    def testInstall(self):
        with open('CONFIG.U6', 'rb') as f:
            self.assertEqual(f.read(), b'\x76\x6d\x61\x33\x38\x38\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
