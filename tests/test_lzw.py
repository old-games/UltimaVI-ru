import hashlib
import os
import random

import tests
import tools
import tools.lzw


class TestLZW(tests.TestCase):
    def testDecompress(self):
        with open(os.path.join(self.script_path, 'original', 'U6.SET'), 'rb') as f:
            self.assertEqual(
                hashlib.sha256(tools.lzw.decompress(f.read())).hexdigest(),
                '6c8b2696de441dff6a35a36dd73986adcceab3dbe45c55939f7c217ad6239250'
            )

    def testCompress(self):
        with open(os.path.join(self.script_path, 'original', 'U6.SET'), 'rb') as f:
            data = tools.lzw.decompress(f.read())*10
        size = len(data)
        data.extend([42]*size)
        random.seed(42)
        data.extend(random.choices([1, 2, 3, 4, 5, 6, 7, 8], k=size))
        data.extend(random.choices(range(256), k=size))
        data.extend(list(range(256))*(size//256))

        for level in (-1, 0, 1, 2):
            with self.subTest(level=level):
                compressed = tools.lzw.compress(data, level=level)
                self.assertEqual(tools.lzw.decompress(compressed), data)

    def testCompressSmall(self):
        for size in range(3):
            with self.subTest(size=size):
                data = b'a'*size
                for level in (-1, 0, 1, 2):
                    with self.subTest(level=level):
                        compressed = tools.lzw.compress(data, level=level)
                        self.assertEqual(tools.lzw.decompress(compressed), data)

    def testCompareCompress(self):
        files = tools.get_compressed_files()

        compressed = 0
        uncompressed = 0
        data = {}
        for name in files:
            with open(os.path.join(self.script_path, 'original', name), 'rb') as f:
                data_compressed = f.read()
            data[name] = tools.lzw.decompress(data_compressed)
            compressed += len(data_compressed)
            uncompressed += len(data[name])
        print(f'Compression rate: {uncompressed/compressed*100:6.03f}%, level=original')

        for level in (-1, 0, 1, 2):
            with self.subTest(level=level):
                compressed = 0
                uncompressed = 0
                for name in files:
                    data_compressed = tools.lzw.compress(data[name], level=level)
                    data_uncompressed = tools.lzw.decompress(data_compressed)
                    self.assertEqual(data_uncompressed, data[name])
                    compressed += len(data_compressed)
                    uncompressed += len(data_uncompressed)
                print(f'Compression rate: {uncompressed/compressed*100:6.03f}%, level={level}')
