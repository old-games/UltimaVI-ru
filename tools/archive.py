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

    digest = hashlib.sha256(data).hexdigest()

    if digest == '8e4620f39d62734fbe4de29e5fa28103da706c6dcf08cfcf6d12c71070faf274':
        # Missed offset in `CONVERSE.A`.
        offsets[0x275c2] = len(items)
        items.append(None)

    elif digest == 'a57af531466a563db991ceae6b633dc04366067c676071bff00455a666272d0a':
        # Missed offset in `PORTRAIT.A`.
        offsets[0x2261e] = len(items)
        items.append(None)

    elif digest == 'ab2ba2eed4d1aff46f15ea7026c948eb9c03638fc5a1b03e0a36ded0fee576a4':
        # Missed offset in `PORTRAIT.B`.
        offsets[0x21b62] = len(items)
        items.append(None)

    elif digest == 'b9e7b293d699279f1ff9f13bd86d0bace5a3fddc963d5573f5acd0ef97830a56':
        # Missed offset in `PORTRAIT.Z`.
        offsets[0x48b9] = len(items)
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
    for i, data in enumerate(list(path)):
        if data is None:
            result.append(None)
        elif hashlib.sha256(data).hexdigest() == '52484ae256cef6191b79c2a09c070198cf1fdc067675ebc54fe930093f0409a7':
            # Uncompressed entry in `CONVERSE.B`.
            # TODO check logic in the game and make this condition less strict probably.
            result.append(data[4:])
        else:
            result.append(tools.lzw.decompress(data))

    return result
