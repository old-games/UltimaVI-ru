def replace(d, a, c):
    d[a:a+len(c)] = c


def patch_END(d):
    # Высота текста "From its crimson depths Lord British emerges, trailed by"
    assert d[0x1749] == 0x92
    assert d[0x175b] == 0x27
    d[0x1749] -= 4
    d[0x175b] += 8


def patch_GAME(d):
    # 0x0464:0x33d3, putch
    assert d[0xb203:0xb206] == b'\x0d\x80\x00'
    replace(d, 0xb204, b'\x00\x01')
