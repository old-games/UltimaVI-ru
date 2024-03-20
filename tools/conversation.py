import hashlib
import io


def _read_char(stream, visited_labels):
    visited_labels.add(stream.tell())
    char = stream.read(1)
    assert char
    return char


def _peek_byte(stream):
    data = stream.peek(1)
    return data[0] if data else None


def _read_byte(stream, visited_labels):
    visited_labels.add(stream.tell())
    return ord(_read_char(stream, visited_labels))


def _check_byte(stream, visited_labels, byte):
    return _peek_byte(stream) == byte and _read_byte(stream, visited_labels) == byte


def _read_dword(stream, visited_labels):
    visited_labels |= set(range(stream.tell(), stream.tell()+4))
    return int.from_bytes(stream.read(4), 'little')


def _read_word(stream, visited_labels):
    visited_labels |= set(range(stream.tell(), stream.tell()+2))
    return int.from_bytes(stream.read(2), 'little')


def _read_string(stream, visited_labels, end):
    result = []
    while _peek_byte(stream) not in end:
        result.append(_read_char(stream, visited_labels))
    return b''.join(result).decode('ascii')


def _read_expression(stream, visited_labels):
    result = []

    operators = {
        0x81, 0x82, 0x83, 0x84, 0x85, 0x86,
        0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x9a, 0x9b, 0x9d, 0x9f,
        0xa0, 0xa8, 0xab,
        0xb2, 0xb3, 0xb4, 0xb7, 0xbb,
        0xc6, 0xc7, 0xca, 0xcc,
        0xd7, 0xda, 0xdc, 0xdd,
        0xe0, 0xe1, 0xe2, 0xe3, 0xe4,
    }

    while (code := _peek_byte(stream)) != 0xa7:
        if code == 0xd2:
            _read_byte(stream, visited_labels)
            result.append(('dword', _read_dword(stream, visited_labels)))

        elif code == 0xd3:
            _read_byte(stream, visited_labels)
            result.append(('byte', _read_byte(stream, visited_labels)))

        elif code == 0xd4:
            _read_byte(stream, visited_labels)
            result.append(('word', _read_word(stream, visited_labels)))

        elif code in operators:
            result.append(_read_byte(stream, visited_labels))

        else:
            result.append(_read_byte(stream, visited_labels))

    _read_byte(stream, visited_labels)
    return ', '.join(map(str, result))


def _is_ended(result):
    # TODO include this to _read_instructions call
    if not result:
        return False
    elif result[-1] == 'BYE' or result[-1][0] == 'JUMP':
        return True
    elif result[-1][0] == 'IF':
        return _is_ended(result[-1][2]) and _is_ended(result[-1][3])
    elif result[-1][0] == 'KEYWORDS':
        # FIXME skips in keywords, check if it is full set, nested keywords
        keywords = []
        choices = None
        for i in range(len(result)-1, -1, -1):
            if result[i][0] == 'ASKC':
                choices = result[i][1]
            elif result[i][0] != 'KEYWORDS':
                break
            elif not _is_ended(result[i][2]):
                return False
            else:
                keywords.extend(result[i][1].split(','))
        if '*' in keywords or choices is not None and set(choices) == set(keywords):
            return True
        else:
            return False
    else:
        return False


def _read_instructions(stream, labels, visited_labels, add_a2, allow_drop_esac, end):
    result = []

    all_instructions = {
        0x9c, 0x9e,
        0xa1, 0xa4, 0xa5, 0xa6,
        0xb0, 0xb5, 0xb6, 0xb9, 0xba, 0xbe, 0xbf,
        0xc4, 0xc5, 0xc9, 0xcb, 0xcd,
        0xd6, 0xd8, 0xd9, 0xdb,
        0xef,
        0xf7, 0xf8, 0xf9, 0xfb, 0xfc,
    }
    if add_a2:
        all_instructions.add(0xa2)

    # TODO there are more instructions in the game
    while (code := _peek_byte(stream)) not in end and stream.tell() not in visited_labels:
        if code == 0x9c:
            _read_byte(stream, visited_labels)
            result.append(('HORSE', _read_expression(stream, visited_labels)))

        elif code == 0x9e:
            _read_byte(stream, visited_labels)
            result.append('SLEEP')

        elif code == 0xa1:
            _read_byte(stream, visited_labels)
            expression = _read_expression(stream, visited_labels)
            sub_visited_labels = set()
            instructions = _read_instructions(stream, labels, sub_visited_labels, add_a2, allow_drop_esac, {0xa2, 0xa3})
            visited_labels |= sub_visited_labels
            if _read_byte(stream, visited_labels) == 0xa3:
                sub_visited_labels = set()
                alternative_instructions = _read_instructions(stream, labels, sub_visited_labels, add_a2, allow_drop_esac, {0xa2})
                visited_labels |= sub_visited_labels
                _read_byte(stream, visited_labels)
            else:
                alternative_instructions = tuple()
            result.append(('IF', expression, instructions, alternative_instructions))

        elif code == 0xa2 and add_a2:
            # `0xa2` added because sometimes it happens (Valkadesh).
            _read_byte(stream, visited_labels)
            result.append('ENDIF')

        elif code == 0xb0:
            _read_byte(stream, visited_labels)
            label = _read_dword(stream, visited_labels)
            result.append(('JUMP', label))
            labels.add(label)

        elif code == 0xb6:
            _read_byte(stream, visited_labels)
            result.append('BYE')

        elif code == 0xa4:
            _read_byte(stream, visited_labels)
            left = _read_expression(stream, visited_labels)
            right = _read_expression(stream, visited_labels)
            result.append(('SETF', left, right))

        elif code == 0xa5:
            _read_byte(stream, visited_labels)
            left = _read_expression(stream, visited_labels)
            right = _read_expression(stream, visited_labels)
            result.append(('CLEARF', left, right))

        elif code == 0xa6:
            _read_byte(stream, visited_labels)
            result.append(('DECL', _read_expression(stream, visited_labels)))

        elif code == 0xb5:
            _read_byte(stream, visited_labels)
            result.append(('DPRINT', _read_expression(stream, visited_labels)))

        elif code == 0xb9:
            _read_byte(stream, visited_labels)
            result.append(('NEW', _read_expression(stream, visited_labels), _read_expression(stream, visited_labels), _read_expression(stream, visited_labels), _read_expression(stream, visited_labels)))

        elif code == 0xba:
            _read_byte(stream, visited_labels)
            result.append(('DELETE', _read_expression(stream, visited_labels), _read_expression(stream, visited_labels), _read_expression(stream, visited_labels), _read_expression(stream, visited_labels)))

        elif code == 0xbe:
            _read_byte(stream, visited_labels)
            result.append(('INVENTORY', _read_expression(stream, visited_labels)))

        elif code == 0xbf:
            _read_byte(stream, visited_labels)
            result.append(('PORTRAIT', _read_expression(stream, visited_labels)))

        elif code == 0xc4:
            _read_byte(stream, visited_labels)
            result.append(('ADD_KARMA', _read_expression(stream, visited_labels)))

        elif code == 0xc5:
            _read_byte(stream, visited_labels)
            result.append(('SUB_KARMA', _read_expression(stream, visited_labels)))

        elif code == 0xc9:
            _read_byte(stream, visited_labels)
            result.append(('GIVE', _read_expression(stream, visited_labels), _read_expression(stream, visited_labels), _read_expression(stream, visited_labels), _read_expression(stream, visited_labels)))

        elif code == 0xcb:
            _read_byte(stream, visited_labels)
            result.append('WAIT')

        elif code == 0xcd:
            _read_byte(stream, visited_labels)
            result.append(('WORKTYPE', _read_expression(stream, visited_labels), _read_expression(stream, visited_labels)))

        elif code == 0xd6:
            _read_byte(stream, visited_labels)
            result.append(('RESURRECT', _read_expression(stream, visited_labels)))

        elif code == 0xd8:
            _read_byte(stream, visited_labels)
            result.append(('SETNAME', _read_expression(stream, visited_labels)))

        elif code == 0xd9:
            _read_byte(stream, visited_labels)
            result.append(('HEAL', _read_expression(stream, visited_labels)))

        elif code == 0xdb:
            _read_byte(stream, visited_labels)
            result.append(('CURE', _read_expression(stream, visited_labels)))

        elif code == 0xef:
            # TODO can't have nested keywords
            while (code := _peek_byte(stream)) == 0xef:
                _read_byte(stream, visited_labels)
                keywords = _read_string(stream, visited_labels, {0xf6})
                _read_byte(stream, visited_labels)
                sub_visited_labels = set()
                instructions = _read_instructions(stream, labels, sub_visited_labels, add_a2, allow_drop_esac, {0xef, 0xee})
                visited_labels |= sub_visited_labels
                result.append(('KEYWORDS', keywords, instructions))

            if allow_drop_esac:
                if _peek_byte(stream) == 0xee:
                    _read_byte(stream, visited_labels)

                else:
                    assert _is_ended(result) and (None in end or 0xee in end)

            else:
                assert _read_byte(stream, visited_labels) == 0xee

        elif code == 0xf7:
            _read_byte(stream, visited_labels)
            result.append('ASK')

        elif code == 0xf8:
            _read_byte(stream, visited_labels)
            result.append(('ASKC', _read_string(stream, visited_labels, end | all_instructions)))

        elif code == 0xf9:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            var = _read_byte(stream, visited_labels)
            assert var in (0xb2, 0xb3)
            result.append(('INPUTSTR', number))

        elif code == 0xfb:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            var = _read_byte(stream, visited_labels)
            assert var in (0xb2, 0xb3)
            result.append(('INPUT', number))

        elif code == 0xfc:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            var = _read_byte(stream, visited_labels)
            assert var in (0xb2, 0xb3)
            result.append(('INPUTNUM', number))

        else:
            result.append(_read_string(stream, visited_labels, end | all_instructions))

        if _peek_byte(stream) is None or _is_ended(result) and (None in end or 0xee in end and allow_drop_esac):
            # Выходим, если читать больше нечего или не ждём окончания определённого блока.
            break

    return result


def decode(data):
    stream = io.BufferedReader(io.BytesIO(data))
    result = {}
    labels = set()
    visited_labels = set()

    digest = hashlib.sha256(data).hexdigest()

    allow_drop_esac = digest in (
        '57e9da766ab59e6022b3446805f98a93869505a21217595fd87a8ef91e00d634',
        '7e8924944c3a1a04c8311b0b7ceab5c255d916854a761431e8385f5645774eb0',
        '8464e3db9e7067ecb8c681f343377bbe208acc7a99cab0c333c22d1bdb65bb68',
        'e7bd3bf7f3d17519d53bbf02929a3fd05dc0600e9891dd21cb18be21f7117481',
        'd28ad8bf501c1a64aca497885364a71799cb68c30dbdade68524b1767e953773',
        'd8fd7702c0201cff8140b573ca59aa91bb65bc2e09370b5bcc1b51e278310020',
    )

    add_a2 = digest == '85f1912ed262ba67a28fdff87c31575d6dd2cea0fbf431ef73e2be77d0958a0d'

    assert _read_byte(stream, visited_labels) == 0xff
    result['id'] = _read_byte(stream, visited_labels)
    result['name'] = _read_string(stream, visited_labels, {0xf1, 0xf3})
    result['f3-after-name'] = _check_byte(stream, visited_labels, 0xf3)

    assert _read_byte(stream, visited_labels) == 0xf1
    result['description'] = _read_instructions(stream, labels, visited_labels, add_a2, allow_drop_esac, {0xf2, 0xf3})
    result['f3-after-description'] = _check_byte(stream, visited_labels, 0xf3)

    assert _read_byte(stream, visited_labels) == 0xf2
    result['conversation'] = {stream.tell(): _read_instructions(stream, labels, visited_labels, add_a2, allow_drop_esac, {None})}

    while labels - visited_labels:
        label = next(iter(labels - visited_labels))
        stream.seek(label)
        result['conversation'][label] = _read_instructions(stream, labels, visited_labels, add_a2, allow_drop_esac, {None})
        # FIXME split code with label in the middle, sometimes in the middle of string

    result['conversation'] = dict(sorted(result['conversation'].items()))

    #import unittest
    #unittest.TestCase().assertEqual(set(range(len(data))) - visited_labels, set())
    return result
