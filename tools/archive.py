import os

import tools
import tools.lzw


def unpack(path):
    items = []
    offsets = {}
    current = 0
    with open(path, 'rb') as f:
        while True:
            offset = int.from_bytes(f.read(4), 'little')
            current += 4
            if current in offsets:
                break
            elif offset != 0:
                assert offset not in offsets
                offsets[offset] = len(items)
            items.append(None)
        size = os.path.getsize(path)
        assert size not in offsets
        offsets[size] = None

        offsets_right = iter(offsets)
        next(offsets_right)
        for (left, index), right in zip(offsets.items(), offsets_right):
            f.seek(left)
            items[index] = f.read(right-left)

    basename = os.path.basename(path)
    name = os.path.splitext(basename)[0]

    result = []
    for i, data in enumerate(items):
        if data:
            if data[:4] == b'\x00\x00\x00\x00' and i == 26 and basename == 'CONVERSE.B':
                result.append(data[4:])
            elif i == 97 and basename == 'CONVERSE.A':
                assert len(items) == i+1 or items[i+1] is None
                data, rest = data[:-1397], data[-1397:]
                result.append(tools.lzw.decompress(data))
                result.append(tools.lzw.decompress(rest))
            elif name == 'PORTRAIT':
                result.append(data)
            else:
                result.append(tools.lzw.decompress(data))
        else:
            result.append(None)

    return result
