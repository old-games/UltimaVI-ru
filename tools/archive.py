import hashlib
import os

import tools
import tools.lzw


def list(path):
    items = []
    offsets = {}
    with open(path, 'rb') as f:
        data = bytearray(f.read())

    current = 0
    while current < len(data):
        offset = int.from_bytes(data[current:current+4], 'little')
        current += 4
        if current in offsets:
            break
        elif offset != 0:
            assert offset not in offsets
            offsets[offset] = len(items)
        items.append(None)

    if hashlib.sha256(data).hexdigest() == '8e4620f39d62734fbe4de29e5fa28103da706c6dcf08cfcf6d12c71070faf274':
        # Missed conversation offset in `CONVERSE.A`.
        offsets[0x275c2] = len(items)
        items.append(None)

    size = len(data)
    assert size not in offsets
    offsets[size] = None

    offsets_right = iter(offsets)
    next(offsets_right)
    for (left, index), right in zip(offsets.items(), offsets_right):
        assert right >= left
        items[index] = data[left:right]

    return items


def unpack(path):
    name = os.path.splitext(os.path.basename(path))[0]

    result = []
    for data in list(path):
        if data is None or name == 'PORTRAIT':
            result.append(data)
        elif hashlib.sha256(data).hexdigest() == '52484ae256cef6191b79c2a09c070198cf1fdc067675ebc54fe930093f0409a7':
            # Uncompressed entry in `CONVERSE.B`.
            result.append(data[4:])
        else:
            result.append(tools.lzw.decompress(data))

    return result
