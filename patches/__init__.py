add_functions = {
    'END.EXE': {
    },
    'GAME.EXE': {
        # FIXME switch to global names in asm files — что я здесь имел в виду?
        'putch': (0x464, 0x33d3, 0x24e),
        'putch_impl': (0x464, 0x2efa, 0x3e4),
        'gets': (0x464, 0x2d3a, 0xcf),
        'get_character_name': (0xecb, 0xa0, 0x76),
        'parse_statement': (0xecb, 0x1c45, 0xbc),
        'tolower': (0x2ce3, 2, 0x31),
        'toupper': (0x2ce6, 3, 0x31),
    },
    'INSTALL.EXE': {
    },
    'U.EXE': {
    },
}


def replace(d, a, c):
    d[a:a+len(c)] = c


def patch_U(d):
    # Ширина текста "Outside, a chill wind rises...".
    assert d[0xb750] == 0x28
    assert d[0xb762] == 0xea
    d[0xb750] -= 4
    d[0xb762] += 8

    # Высота текста "At first the plain is still. Then a hundred voices ".
    assert d[0xcda2] == 0xa0
    assert d[0xcdb4] == 0x1f
    d[0xcda2] -= 4
    d[0xcdb4] += 8

    # Высота текста "Friendly faces vault from a newborn moongate, while a "
    assert d[0xd23f] == 0xa0
    assert d[0xd251] == 0x1f
    d[0xd23f] -= 4
    d[0xd251] += 8

    #d[0x69d4] = 0xeb

    #d[0x3369] = 0x90
    #d[0x336a] = 0x90

    #d[0xb431] = 0x90
    #d[0xb432] = 0x90

    #d[0x9a3e] = 0x90
    #d[0x9a3d] = 0x90

    #d[0x8c1b] = 0xeb

    """ One of these used in transfer character
    d[0xd7fb] = 0xeb

    d[0x36fa] = 0xeb

    d[0x2c70] = 0xeb
    """

    # Ввод русских букв.
    assert set(d[0x1a5cb:0x1a64b]) == {0}
    alpha = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    six = alpha[:6]
    assert len(set(alpha)) == 33
    for letter in alpha:
        code = ord(letter.encode('cp866'))
        d[0x1a5cb+code-0x80] |= 8
    for letter in alpha.upper():
        code = ord(letter.encode('cp866'))
        d[0x1a5cb+code-0x80] |= 4
    for letter in six + six.upper():
        code = ord(letter.encode('cp866'))
        d[0x1a5cb+code-0x80] |= 0x10

    # Return code is word.
    assert d[0x2a91] == 0x8a
    d[0x2a91] = 0x8b

    # Use word.
    assert d[0x2afc] == 0x98
    d[0x2afc] = 0x90

    # FIXME
    0x13e68
    0x13e75
    0x13e82
    0x13f4a
    0x13f6b
    0x13f7c


def patch_END(d):
    # Высота текста "From its crimson depths Lord British emerges, trailed by ".
    assert d[0x1749] == 0x92
    assert d[0x175b] == 0x27
    d[0x1749] -= 4
    d[0x175b] += 8

    # Высота текста "You pick up the concave lens and pass it to the King. ".
    assert d[0x186f] == 0x8e
    assert d[0x1881] == 0x2f
    d[0x186f] -= 4
    d[0x1881] += 8

    # Высота текста "As Lord British holds the glass before the ".
    assert d[0x18f5] == 0xa3
    assert d[0x1907] == 0x17
    d[0x18f5] -= 4
    d[0x1907] += 8

    # Высота текста "King Draxinusom of the Gargoyles strides forward, ".
    assert d[0x1a06] == 0x8e
    assert d[0x1a18] == 0x2f
    d[0x1a06] -= 4
    d[0x1a18] += 8

    # Высота текста "...and you press it into the hand of the towering ".
    assert d[0x1b35] == 0xa3
    assert d[0x1b47] == 0x17
    d[0x1b35] -= 4
    d[0x1b47] += 8

    # Высота текста "At your urging, King Draxinusom reluctantly raises his ".
    assert d[0x1ba1] == 0x92
    assert d[0x1bb3] == 0x27
    d[0x1ba1] -= 4
    d[0x1bb3] += 8

    # Высота текста "The ancient book opens. Both kings gaze upon its pages in ".
    assert d[0x1c16] == 0x92
    assert d[0x1c28] == 0x27
    d[0x1c16] -= 4
    d[0x1c28] += 8


def patch_GAME(d):
    # 0x464:0x33d3, putch, проверка на 0x80 бит.
    assert d[0xb203:0xb206] == b'\x0d\x80\x00'
    replace(d, 0xb204, b'\x00\x01')

    # Conversation format version 2.
    replaces = {
        (0xf1, 1): [0x142fd, 0x14358],
        (0xa2, 2): [0x13acb, 0x13b0e],
        (0xa3, 3): [0x13ac3],
        (0xee, 0x0e): [0x140b1, 0x14627],
        (0xef, 0x0f): [0x140ab, 0x140bd, 0x1459a, 0x1460b],
    }
    for (expected, fix), offsets in replaces.items():
        for offset in offsets:
            assert d[offset] == expected
            d[offset] = fix
