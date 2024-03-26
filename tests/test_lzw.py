import hashlib
import os
import random
import time

import tests
import tools
import tools.archive
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

        for level in tools.lzw.get_compression_levels():
            with self.subTest(level=level):
                compressed = tools.lzw.compress(data, level=level)
                self.assertEqual(tools.lzw.decompress(compressed), data)

    def testSmall(self):
        for size in range(50):
            with self.subTest(size=size):
                data = b'a'*size
                for level in tools.lzw.get_compression_levels():
                    with self.subTest(level=level):
                        compressed = tools.lzw.compress(data, level=level)
                        self.assertEqual(tools.lzw.decompress(compressed), data)

    def testOneBit(self):
        size = 1024*64
        data = bytearray()
        data.extend([1]*size)
        data.extend([0, 1]*(size//2))
        random.seed(27)
        data.extend(random.choices([0, 1], k=size))

        for max_codeword_size in (2, 3, 6):
            with self.subTest(max_codeword_size=max_codeword_size):
                for level in tools.lzw.get_compression_levels(min_codeword_size=2, max_codeword_size=max_codeword_size):
                    with self.subTest(level=level):
                        compressed = tools.lzw.compress(data, level=level, min_codeword_size=2, max_codeword_size=max_codeword_size)
                        self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=2, max_codeword_size=max_codeword_size), data)

    def testSmallOneBit(self):
        for size in range(50):
            with self.subTest(size=size):
                data = bytearray([1]*size)
                for max_codeword_size in (2, 3, 6):
                    with self.subTest(max_codeword_size=max_codeword_size):
                        for level in tools.lzw.get_compression_levels(min_codeword_size=2, max_codeword_size=max_codeword_size):
                            with self.subTest(level=level):
                                compressed = tools.lzw.compress(data, level=level, min_codeword_size=2, max_codeword_size=max_codeword_size)
                                self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=2, max_codeword_size=max_codeword_size), data)

    def testTwoBits(self):
        size = 1024*64
        data = bytearray()
        data.extend([1]*size)
        data.extend([0, 1, 2, 3]*(size//4))
        random.seed(137)
        data.extend(random.choices([0, 1], k=size))
        data.extend(random.choices([0, 1, 2], k=size))
        data.extend(random.choices([0, 1, 2, 3], k=size))

        for max_codeword_size in (3, 7):
            with self.subTest(max_codeword_size=max_codeword_size):
                for level in tools.lzw.get_compression_levels(min_codeword_size=3, max_codeword_size=max_codeword_size):
                    with self.subTest(level=level):
                        compressed = tools.lzw.compress(data, level=level, min_codeword_size=3, max_codeword_size=max_codeword_size)
                        self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=3, max_codeword_size=max_codeword_size), data)

    def testSmallTwoBits(self):
        for size in range(50):
            with self.subTest(size=size):
                data = bytearray([3]*size)
                for max_codeword_size in (3, 7):
                    with self.subTest(max_codeword_size=max_codeword_size):
                        for level in tools.lzw.get_compression_levels(min_codeword_size=3, max_codeword_size=max_codeword_size):
                            with self.subTest(level=level):
                                compressed = tools.lzw.compress(data, level=level, min_codeword_size=3, max_codeword_size=max_codeword_size)
                                self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=3, max_codeword_size=max_codeword_size), data)

    # FIXME test on int array

    def testNoPadding(self):
        with self.subTest(level=-1):
            data = bytearray([1, 0, 1, 0, 1, 0])
            compressed = tools.lzw.compress(data, level=-1, min_codeword_size=2, max_codeword_size=3)
            self.assertEqual(compressed, b'\x06\x00\x00\x00&\x94Pb')
            self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=2, max_codeword_size=3), data)

        for level in (0, 1):
            with self.subTest(level=level):
                data = bytearray([1, 2, 3, 1, 2, 3, 1, 2, 3, 1])
                compressed = tools.lzw.compress(data, level=level, min_codeword_size=3, max_codeword_size=7)
                self.assertEqual(compressed, b'\n\x00\x00\x00\x8c\xb8Pc\xc4\xa5')
                self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=3, max_codeword_size=7), data)

        for level in (2, 3):
            with self.subTest(level=level):
                data = bytearray([1, 2, 3])
                compressed = tools.lzw.compress(data, level=level, min_codeword_size=3, max_codeword_size=7)
                self.assertEqual(compressed, b'\x03\x00\x00\x00\x8cV')
                self.assertEqual(tools.lzw.decompress(compressed, min_codeword_size=3, max_codeword_size=7), data)

    def testCompare(self):
        # TODO probably also need test on built files
        data = {}
        compressed = 0
        uncompressed = 0
        archives = tools.get_archive_files()
        for archive in archives:
            if os.path.splitext(archive)[0] != 'PORTRAIT':
                items = tools.archive.decode(os.path.join(self.script_path, 'original', archive))
                for i, item in enumerate(items):
                    if item is not None and int.from_bytes(item[:4], 'little') != 0:
                        data_uncompressed = tools.lzw.decompress(item)
                        data[f'{archive}[{i}]'] = {'compressed': item, 'uncompressed': data_uncompressed}
                        compressed += len(item)
                        uncompressed += len(data_uncompressed)

        files = tools.get_compressed_files()
        for name in files:
            with open(os.path.join(self.script_path, 'original', name), 'rb') as f:
                data_compressed = f.read()
            data[name] = {'compressed': data_compressed, 'uncompressed': tools.lzw.decompress(data_compressed)}
            compressed += len(data_compressed)
            uncompressed += len(data[name]['uncompressed'])

        print(f'Compression rate: {uncompressed/compressed*100:7.03f}%, level=original')

        for level in tools.lzw.get_compression_levels():
            with self.subTest(level=level):
                compressed = 0
                t = time.monotonic()
                for name in data:
                    data_compressed = tools.lzw.compress(data[name]['uncompressed'], level=level)
                    data_uncompressed = tools.lzw.decompress(data_compressed)
                    self.assertEqual(data_uncompressed, data[name]['uncompressed'])
                    if level == 2 and data_compressed != data[name]['compressed']:
                        print(f'{name} does not match, original: {len(data[name]["compressed"])}, level=2: {len(data_compressed)}')
                    elif level == 3:
                        self.assertEqual(data_compressed, data[name]['compressed'])
                    compressed += len(data_compressed)
                t = time.monotonic() - t

                print(f'Compression rate: {uncompressed/compressed*100:7.03f}%, level={level}, time={t:.2f}s')
