import hashlib
import os

import tools
import tools.lzw


def decode(path):
    items = []
    offsets = {}
    with open(path, 'rb') as f:
        data = bytearray(f.read())

    current = 0
    while current < len(data):
        offset = int.from_bytes(data[current:current+4], 'little')
        if current in offsets:
            break
        elif offset != 0:
            assert offset not in offsets
            offsets[offset] = len(items)
        items.append(None)
        current += 4

    assert current == next(iter(offsets))

    size = len(data)
    assert size not in offsets
    offsets[size] = None

    offsets_right = iter(offsets)
    next(offsets_right)
    for (left, index), right in zip(offsets.items(), offsets_right):
        assert right >= left
        items[index] = data[left:right]

    return items


def encode(data, path):
    offsets = [len(data)*4]
    for item in data:
        offsets.append(offsets[-1] + (len(item) if item is not None else 0))

    with open(path, 'wb') as f:
        for offset, item in zip(offsets, data):
            f.write(offset.to_bytes(4, 'little') if item is not None else b'\x00'*4)
        for offset, item in zip(offsets, data):
            if item is not None:
                assert f.tell() == offset
                f.write(item)
        assert f.tell() == offsets[-1]


def unpack(path):
    # FIXME test
    result = []
    for item in decode(path):
        if item is None:
            result.append(None)
        elif hashlib.sha256(item).hexdigest() == '52484ae256cef6191b79c2a09c070198cf1fdc067675ebc54fe930093f0409a7':
            # Uncompressed entry in `CONVERSE.B`.
            # TODO check logic in the game and make this condition less strict probably.
            result.append(item[4:])
        else:
            result.append(tools.lzw.decompress(item))

    return result


def pack(data, path):
    # FIXME test
    compressed = []
    for item in data:
        compressed.append(item and tools.lzw.compress(item))
    encode(compressed, path)
