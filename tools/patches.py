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
    # 0x0464:0x33d3, putch, проверка на 0x80 бит.
    assert d[0xb203:0xb206] == b'\x0d\x80\x00'
    replace(d, 0xb204, b'\x00\x01')