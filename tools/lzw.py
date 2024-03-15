import collections


def _slice_deque(deque, index, size):
    result = []
    for i in range(index, size):
        result.append(deque[i])
    #print(result)
    return tuple(result)


def _codeword_to_int(codeword):
    b = 0
    for j, bit in enumerate(codeword):
        b |= bit << j
    return b


def _int_to_codeword(x, codeword_size):
    assert x < 1 << codeword_size
    codeword = []
    for j in range(codeword_size):
        codeword.append(1 if x & 1 << j else 0)
    return codeword


def decompress(data, min_codeword_size=9, max_codeword_size=12):
    size = int.from_bytes(data[:4], 'little')
    max_codeword_size = max_codeword_size
    min_extended_codeword = (1 << min_codeword_size - 1) + 2
    max_value = 1 << min_codeword_size - 1
    bits = collections.deque()
    for i in data[4:]:
        for j in range(8):
            bits.append(1 if (1 << j) & i else 0)
    assert len(bits) >= min_codeword_size

    new_strings = [bytes([x]) for x in range(max_value)]
    new_strings.append('INIT')
    new_strings.append('EOF')

    codeword_size = min_codeword_size
    strings = new_strings.copy()
    string = b''
    result = bytearray()
    while bits:
        codeword = _codeword_to_int(_slice_deque(bits, 0, codeword_size))
        for _ in range(codeword_size):
            bits.popleft()

        if codeword == max_value:
            codeword_size = min_codeword_size
            strings = new_strings.copy()
            string = b''
            continue

        elif codeword == max_value + 1:
            break

        else:
            if codeword < len(strings):
                if len(string):
                    # Дополнительный символ всегда приходит в начале следующей строке.
                    strings.append(string + strings[codeword][:1])

            else:
                assert codeword == len(strings), f'{codeword} != {len(strings)}'
                # Следующая строка это как раз наша, берём символ оттуда.
                strings.append(string + string[:1])

            if len(strings) >= 1 << codeword_size and codeword_size < max_codeword_size:
                codeword_size += 1

            string = strings[codeword]
            result.extend(string)

    assert len(result) == size
    assert len(bits) < 8
    assert set(bits) <= {0}
    return result


def get_compression_levels():
    return (-1, 0, 1, 2, 3)


def compress(data, level=2, min_codeword_size=9, max_codeword_size=12):
    assert level in get_compression_levels()
    max_value = 1 << min_codeword_size - 1
    max_safe_block_size = max_value - 2
    bits = []

    # TODO можно ли писать дальше конца словаря?
    # TODO научиться в любой момент сбрасывать словарь
    # TODO можно ли игнорить запись EOF

    # TODO Для строк нулевой длины отправляется только EOF. Проверить правильно ли это.
    if level == -1:
        for i, char in enumerate(data):
            bits.extend(_int_to_codeword(max_value, min_codeword_size))
            bits.extend(_int_to_codeword(char, min_codeword_size))
        bits.extend(_int_to_codeword(max_value+1, min_codeword_size))

    elif level == 0:
        for i, char in enumerate(data):
            if i % max_safe_block_size == 0:
                bits.extend(_int_to_codeword(max_value, min_codeword_size))
            bits.extend(_int_to_codeword(char, min_codeword_size))
        bits.extend(_int_to_codeword(max_value+1, min_codeword_size))

    elif level == 1:
        new_strings = {bytes([x]): x for x in range(max_value)}
        new_strings['INIT'] = len(new_strings)
        new_strings['EOF'] = len(new_strings)

        codeword_size = min_codeword_size
        string = b''
        strings = new_strings.copy()
        i = 0
        for i, char in enumerate(data):
            if i % max_safe_block_size == 0:
                if len(string):
                    bits.extend(_int_to_codeword(strings[string], codeword_size))
                strings = new_strings.copy()
                bits.extend(_int_to_codeword(strings['INIT'], codeword_size))
                codeword_size = min_codeword_size
                string = b''

            bytes_char = bytes([char])
            if string + bytes_char in strings:
                string += bytes_char

            else:
                bits.extend(_int_to_codeword(strings[string], codeword_size))
                strings[string+bytes_char] = len(strings)
                string = bytes_char

                if len(strings) >= 1 << codeword_size and codeword_size < max_codeword_size:
                    codeword_size += 1

        if len(string):
            bits.extend(_int_to_codeword(strings[string], codeword_size))
        bits.extend(_int_to_codeword(strings['EOF'], codeword_size))

    elif level == 2:
        new_strings = {bytes([x]): x for x in range(max_value)}
        new_strings['INIT'] = len(new_strings)
        new_strings['EOF'] = len(new_strings)

        codeword_size = min_codeword_size
        string = b''
        strings = new_strings.copy()
        i = 0
        for i, char in enumerate(data):
            if not i:
                bits.extend(_int_to_codeword(strings['INIT'], codeword_size))

            bytes_char = bytes([char])
            if string + bytes_char in strings:
                string += bytes_char

            else:
                # FIXME здесь можем отправить меньше бит чем надо, если добавляются две подряд строки?
                bits.extend(_int_to_codeword(strings[string], codeword_size))
                if strings[string] == len(strings) - 1:
                    # FIXME почему так выходит, ещё раз?
                    assert string[0] == string[-1]

                strings[string+bytes_char] = len(strings)
                string = bytes_char

                if len(strings) > 1 << codeword_size:
                    # Меняем `codeword_size` "на шаг позже", потому что последний символ ещё не отправили.
                    assert len(strings) - 1 == 1 << codeword_size
                    if codeword_size < max_codeword_size:
                        codeword_size += 1
                    else:
                        bits.extend(_int_to_codeword(strings[string], codeword_size))
                        strings = new_strings.copy()
                        bits.extend(_int_to_codeword(strings['INIT'], codeword_size))
                        codeword_size = min_codeword_size
                        string = b''

        if len(string):
            bits.extend(_int_to_codeword(strings[string], codeword_size))
        bits.extend(_int_to_codeword(strings['EOF'], codeword_size))

    elif level == 3:
        # This one is same to original.
        new_strings = {bytes([x]): x for x in range(max_value)}
        new_strings['INIT'] = len(new_strings)
        new_strings['EOF'] = len(new_strings)

        codeword_size = min_codeword_size
        string = b''
        strings = new_strings.copy()
        i = 0
        for i, char in enumerate(data):
            if not i:
                bits.extend(_int_to_codeword(strings['INIT'], codeword_size))

            bytes_char = bytes([char])
            if string + bytes_char in strings:
                string += bytes_char

            else:
                # FIXME здесь можем отправить меньше бит чем надо, если добавляются две подряд строки?
                bits.extend(_int_to_codeword(strings[string], codeword_size))
                if strings[string] == len(strings) - 1:
                    # FIXME почему так выходит, ещё раз?
                    assert string[0] == string[-1]

                strings[string+bytes_char] = len(strings)
                string = bytes_char

                if len(strings) > 1 << codeword_size:
                    # Меняем `codeword_size` "на шаг позже", потому что последний символ ещё не отправили.
                    assert len(strings) - 1 == 1 << codeword_size
                    if codeword_size < max_codeword_size:
                        codeword_size += 1
                    else:
                        strings = new_strings.copy()
                        bits.extend(_int_to_codeword(strings['INIT'], codeword_size))
                        codeword_size = min_codeword_size

        if len(string):
            bits.extend(_int_to_codeword(strings[string], codeword_size))
        bits.extend(_int_to_codeword(strings['EOF'], codeword_size))

    bits.extend([0] * ((len(bits) + 7) // 8 * 8 - len(bits)))
    assert len(bits) % 8 == 0
    result = bytearray(len(data).to_bytes(4, 'little'))
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b |= bits[i+j] << j
        result.append(b)
    return result
