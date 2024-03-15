import os

import tools
import tools.lzw


def list(path):
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
            assert right >= left
            f.seek(left)
            items[index] = f.read(right-left)

    basename = os.path.basename(path)
    fixed_items = []
    for i, data in enumerate(items):
        if data:
            if basename == 'CONVERSE.A' and i == 97:
                assert len(items) == i+1 or items[i+1] is None
                data, rest = data[:-1397], data[-1397:]
                fixed_items.append(data)
                fixed_items.append(rest)
            else:
                fixed_items.append(data)
        else:
            fixed_items.append(None)

    return fixed_items


def unpack(path):
    basename = os.path.basename(path)
    name = os.path.splitext(basename)[0]

    result = []
    for i, data in enumerate(list(path)):
        if data:
            if basename == 'CONVERSE.B' and i == 26 and int.from_bytes(data[:4], 'little') == 0:
                result.append(data[4:])
            elif name == 'PORTRAIT':
                result.append(data)
            else:
                result.append(tools.lzw.decompress(data))
        else:
            result.append(None)

    return result
