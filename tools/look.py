def decode(data):
    result = {}
    # FIXME test

    index = 0
    while index + 1 < len(data):
        id = int.from_bytes(data[index:index+2], 'little')
        index += 2

        if id != 0x801:
            zero = data.index(b'\x00', index)
            result[id] = data[index:zero].decode('ascii')
            index = zero + 1

    assert index == len(data)
    return result


def encode(look):
    # FIXME test
    pass
