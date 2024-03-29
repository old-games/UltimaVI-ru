import hashlib
import os

import tools
import tools.lzw


def decode(data, bits=32, ordered=True):
    items = []
    offsets = {}

    current = 0
    while current < len(data):
        offset = int.from_bytes(data[current:current+bits//8], 'little')
        if current in offsets:
            break
        elif offset != 0:
            assert offset not in offsets
            offsets[offset] = len(items)
        items.append(None)
        current += bits//8

    assert not ordered or current == next(iter(offsets))

    size = len(data)
    assert size not in offsets
    offsets[size] = None

    if not ordered:
        offsets = dict(sorted(offsets.items()))

    offsets_right = iter(offsets)
    next(offsets_right)
    for (left, index), right in zip(offsets.items(), offsets_right):
        assert right >= left
        items[index] = data[left:right]

    return items


def encode(data, bits=32):
    offsets = [len(data)*(bits//8)]
    for item in data:
        offsets.append(offsets[-1] + (len(item) if item is not None else 0))

    result = bytearray()
    for offset, item in zip(offsets, data):
        result.extend(offset.to_bytes(bits//8, 'little') if item is not None else b'\x00'*(bits//8))
    for offset, item in zip(offsets, data):
        if item is not None:
            assert len(result) == offset
            result.extend(item)

    assert len(result) == offsets[-1]
    return result


def unpack(data):
    # FIXME test
    result = []
    for item in decode(data):
        if item is None:
            result.append(None)
        elif hashlib.sha256(item).hexdigest() == '52484ae256cef6191b79c2a09c070198cf1fdc067675ebc54fe930093f0409a7':
            # Uncompressed entry in `CONVERSE.B`.
            # TODO check logic in the game and make this condition less strict probably.
            result.append(item[4:])
        else:
            result.append(tools.lzw.decompress(item))

    return result


def pack(data):
    # FIXME test
    compressed = []
    for item in data:
        compressed.append(item and tools.lzw.compress(item))

    return encode(compressed)
