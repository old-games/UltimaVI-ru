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


# Дальние вызовы (call far с релокацией сегмента), перенаправляемые на функции из code_block:
# смещение инструкции в файле → (asm-файл, метка, прежний адрес seg:off — для проверки).
redirect_calls = {
    'GAME.EXE': {
        0x9a82: ('hotkeys', 'hotkey_toupper', (0x2ce6, 0x3)),  # toupper в обработчике событий 0x464:0x1d59
        0x7298: ('hotkeys', 'command_getch', (0x464, 0x2a59)),  # цикл команд A B C D G L M R T U
        0x7739: ('hotkeys', 'yes_no_getch', (0x464, 0x2a59)),  # вопросы «да/нет»: getch, затем 'Y'/'N'
        0x7927: ('hotkeys', 'yes_no_getch', (0x464, 0x2a59)),
        0x7964: ('hotkeys', 'yes_no_getch', (0x464, 0x2a59)),
        0x1cefc: ('hotkeys', 'yes_no_getch', (0x464, 0x2a59)),
        0x27b50: ('hotkeys', 'yes_no_getch', (0x464, 0x2a59)),
        0x144c0: ('hotkeys', 'conversation_getch', (0x464, 0x2a59)),  # диалоги: ввод символа (0xfc)
        0x1453e: ('hotkeys', 'conversation_getch', (0x464, 0x2a59)),  # диалоги: ввод символа (0xfa)
        0x145a7: ('hotkeys', 'conversation_getch', (0x464, 0x2a59)),  # диалоги: choice (0xf8)
    },
}


def russian_plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# Массивы строк фиксированной ширины char[count][size]. Массив переносится в конец DS с ячейками new_size,
# в коде правятся ширина (size_refs, imm16) и адрес начала (base_refs, imm16 смещение в DS). Если у копии
# есть units, к элементу i добавляется ' ' + форма слова для числа i, и для каждой копии делается свой массив.
string_arrays = {
    'END.EXE': [
        {
            # char numbers[30][13] — "zero" ... "twenty-nine": mov dx, 13; mul dx; add ax, 0x258; ... strcpy.
            # Затем strcat(" year") и strcat("s"), если не 1, — эти суффиксы в переводе пустые, а годы, месяцы
            # и дни берутся из своих массивов уже с правильной формой. Приёмники — буферы по 64 байта.
            'offset': 34712, 'count': 30, 'size': 13, 'new_size': 32,
            'size_refs': [8507, 8575, 8655],
            'copies': [
                {'base_refs': [8512], 'units': ('год', 'года', 'лет')},
                {'base_refs': [8580], 'units': ('месяц', 'месяца', 'месяцев')},
                {'base_refs': [8660], 'units': ('день', 'дня', 'дней')},
            ],
        },
    ],
}

# (файл, смещение) -> максимальный размер строки вместе с нулём.
fixed_size_strings = {
    (binary, a['offset'] + a['size']*i): a['new_size'] - max(
        (1 + len(u.encode('cp866')) for c in a['copies'] for u in c.get('units', ())), default=0
    )
    for binary, arrays in string_arrays.items() for a in arrays for i in range(a['count'])
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

    # Пол персонажа хранится в DS:0x5a46 буквой ('F'/'M') или словом ("Female"/"Male", переводятся),
    # и везде игра проверяет только первый символ на 'F'. После перевода слов на "Жен"/"Муж" женский пол
    # не распознаётся. Вместо сравнения проверяем бит 3 первого символа: он сброшен у 'F' (0x46) и 'Ж' (0x86)
    # и установлен у 'M' (0x4d) и 'М' (0x8c). Поэтому перевод слова для женского пола должен начинаться
    # с 'Ж', для мужского — с 'М'.
    test_female = b'\xf6\x06\x46\x5a\x08' # test byte [0x5a46], 8

    # Портрет и запись пола в сохранение: cmp byte [0x5a46], 'F' -> test.
    for a in (0x4da4, 0x5abd):
        assert d[a:a+5] == b'\x80\x3e\x46\x5a\x46'
        replace(d, a, test_female)

    # Переключение пола на итоговом экране: 'F' -> "Male", 'M' -> "Female".
    assert d[0x458f:0x459f] == bytes.fromhex('a0465a983d460074193d4d007402eb22')
    replace(d, 0x458f, test_female + bytes.fromhex(
        '741b'          # jz male (0x45b1)
        'eb07'          # jmp female (0x459f)
    ).ljust(11, b'\x90'))

    # Ответ на вопрос "Мужчина ты иль женщина?": принимаем M/F и М/Ж, строчные тоже.
    assert d[0x5d60:0x5d88] == bytes.fromhex('a0465a98509a0f0040124444a2465a803e465a4d740b803e465a4674040bf675c20bf67503e957ff')
    replace(d, 0x5d60, bytes.fromhex(
        'a1465a'        # mov ax, [0x5a46]  ; ah = 0 из терминатора, без cbw, иначе toupper ломается на >= 0x80
        '90'            # nop
        '50'            # push ax
        '9a0f004012'    # lcall toupper (релокация, не трогаем)
        '59'            # pop cx
        'a2465a'        # mov [0x5a46], al
        '0bf6'          # or si, si
        '7412'          # jz back (0x5d84)
        '3c4d7412'      # cmp al, 'M' ; je ok (0x5d88)
        '3c46740e'      # cmp al, 'F' ; je ok
        '3c8c740a'      # cmp al, 'М' ; je ok
        '3c8675c1'      # cmp al, 'Ж' ; jne ask_again (0x5d43)
        'eb04'          # jmp ok
        'e958ff'        # back: jmp 0x5cdf
    ))

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
