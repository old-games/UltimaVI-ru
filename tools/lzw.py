import collections


def _slice_deque(deque, index, size):
    result = []
    for i in range(index, size):
        result.append(deque[i])
    return tuple(result)


def _get_string(codewords, codeword):
    result = []
    while codeword & ~0xff:
        root, codeword = codewords[codeword]
        result.append(root)
    result.append(codeword)
    return result


def _codeword_to_int(codeword):
    b = 0
    for j, bit in enumerate(codeword):
        b |= bit << j
    return b


def unlzw(data):
    size = int.from_bytes(data[:4], 'little')
    index = 4
    codeword_size = 9
    bits = collections.deque()
    for i in data[4:]:
        for j in range(8):
            bits.append(1 if (1 << j) & i else 0)
    assert _slice_deque(bits, 0, 9) == (0, 0, 0, 0, 0, 0, 0, 0, 1)

    codewords = {}

    result = bytearray()
    last_codeword = None
    while bits:
        codeword = _codeword_to_int(_slice_deque(bits, 0, codeword_size))
        for _ in range(codeword_size):
            bits.popleft()

        if codeword == 0x100:
            codeword_size = 9
            codewords = {}
            codeword = _codeword_to_int(_slice_deque(bits, 0, codeword_size))
            for _ in range(codeword_size):
                bits.popleft()
            assert codeword & ~0xff == 0 # TODO WTF is this last bit.
            result.append(codeword & 0xff)

        elif codeword == 0x101:
            break

        else:
            if codeword in codewords or not (codeword & ~0xff):
                string = _get_string(codewords, codeword)
                for x in reversed(string):
                    assert x & ~0xff == 0 # FIXME or wtf with these last bits???
                    result.append(x & 0xff)

            else:
                string = _get_string(codewords, last_codeword)
                for x in reversed([string[-1]] + string): # FIXME WTF, we duplicate a character
                    assert x & ~0xff == 0 # FIXME or wtf with these last bits???
                    result.append(x & 0xff)
                assert codeword == 0x102 + len(codewords)

            codewords[0x102 + len(codewords)] = (string[-1], last_codeword) # string[-1] & 0xff

            if 0x102 + len(codewords) >= 1 << codeword_size:
                codeword_size += 1

        last_codeword = codeword

    assert len(result) == size
    return result
