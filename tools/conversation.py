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
    data = stream.read(4)
    assert len(data) == 4
    visited_labels |= set(range(stream.tell()-4, stream.tell()))
    return int.from_bytes(data, 'little')


def _read_word(stream, visited_labels):
    data = stream.read(2)
    assert len(data) == 2
    visited_labels |= set(range(stream.tell()-2, stream.tell()))
    return int.from_bytes(data, 'little')


def _read_string(stream, visited_labels, end):
    result = []
    while _peek_byte(stream) not in end:
        result.append(_read_char(stream, visited_labels))
    return b''.join(result).decode('ascii')


def _set_data_type(data, offset, type):
    assert data[offset] in (None, type)
    data[offset] = type


def _one(collection):
    assert len(collection) == 1
    return collection[0]


def _read_expressions(stream, visited_labels, data, end):
    operators = {
        0x81: 'greater', 0x82: 'greaterOrEquals', 0x83: 'less', 0x84: 'lessOrEquals', 0x85: 'notEquals', 0x86: 'equals',
        0x90: 'plus', 0x91: 'minus', 0x92: 'multiply', 0x93: 'divide', 0x94: 'or', 0x95: 'and',
        0x9a: 'canCarry', 0x9b: 'weight', 0x9d: 'hasHorse', 0x9f: 'hasObject',
        0xa0: 'random', 0xab: 'hasBit',
        0xb2: 'integer', 0xb3: 'string', 0xb4: 'data', 0xb7: 'indexOf', 0xbb: 'objectsCount',
        0xc6: 'partyHas', 0xc7: 'partyHasObject', 0xca: 'partyJoin', 0xcc: 'partyLeave',
        0xd7: 'isNearby', 0xda: 'isWounded', 0xdc: 'isPoisoned', 0xdd: 'character',
        0xe0: 'experience', 0xe1: 'level', 0xe2: 'strength', 0xe3: 'intelligence', 0xe4: 'dexterity',
    }
    parameters = {operator: 1 for operator in (
        'canCarry', 'hasHorse', 'integer', 'string', 'partyHas', 'partyJoin', 'partyLeave',
        'isNearby', 'isWounded', 'isPoisoned'
    )}
    parameters.update({operator: 2 for operator in operators.values() if operator not in parameters})
    parameters.update({operator: 3 for operator in ('hasObject',)})

    parts = []
    while (code := _peek_byte(stream)) != end:
        if code == 0xd2:
            _read_byte(stream, visited_labels)
            parts.append(('dword', _read_dword(stream, visited_labels)))

        elif code == 0xd3:
            _read_byte(stream, visited_labels)
            parts.append(('byte', _read_byte(stream, visited_labels)))

        elif code == 0xd4:
            _read_byte(stream, visited_labels)
            parts.append(('word', _read_word(stream, visited_labels)))

        elif code in operators:
            parts.append(operators[_read_byte(stream, visited_labels)])

        else:
            assert _peek_byte(stream) < 0x80
            parts.append(('value', _read_byte(stream, visited_labels)))

    _read_byte(stream, visited_labels)

    # FIXME what is `value`? why not `byte`? can we squeeze them to plain value and decide automatically?

    # FIXME what `character` does ? returns string?

    def process_parts(parts, data):
        operator = parts.pop()
        if operator[0] in ('byte', 'word', 'dword', 'value'):
            return operator

        else:
            arguments = []
            for _ in range(parameters[operator]):
                arguments.append(process_parts(parts, data))
            arguments.reverse()

            if operator == 'data':
                assert arguments[0][0] == 'dword'
                data.setdefault(arguments[0][1], None)

            for argument in arguments:
                if argument[0] == 'data':
                    _set_data_type(data, argument[1][0][1], 'integer')

            return (operator, arguments)

    expressions = []
    while parts:
        expressions.append(process_parts(parts, data))

    return expressions


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


def _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, allow_drop_esac, end):
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
    if allow_solo_endif:
        all_instructions.add(0xa2)

    # TODO there are more instructions in the game
    while (code := _peek_byte(stream)) not in end and stream.tell() not in visited_labels:
        if code == 0x9c:
            _read_byte(stream, visited_labels)
            result.append(('HORSE', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0x9e:
            _read_byte(stream, visited_labels)
            result.append('SLEEP')

        elif code == 0xa1:
            _read_byte(stream, visited_labels)
            expression = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            sub_visited_labels = set()
            instructions = _read_instructions(stream, labels, sub_visited_labels, data, allow_solo_endif, allow_drop_esac, {0xa2, 0xa3})
            visited_labels |= sub_visited_labels
            if _read_byte(stream, visited_labels) == 0xa3:
                sub_visited_labels = set()
                alternative_instructions = _read_instructions(stream, labels, sub_visited_labels, data, allow_solo_endif, allow_drop_esac, {0xa2})
                visited_labels |= sub_visited_labels
                _read_byte(stream, visited_labels)
            else:
                alternative_instructions = tuple()
            result.append(('IF', expression, instructions, alternative_instructions))

        elif code == 0xa2 and allow_solo_endif:
            # Sometimes it happens (Valkadesh).
            _read_byte(stream, visited_labels)

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
            left = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            right = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            result.append(('SETF', left, right))

        elif code == 0xa5:
            _read_byte(stream, visited_labels)
            left = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            right = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            result.append(('CLEARF', left, right))

        elif code == 0xa6:
            # TODO support packing and unpacking
            _read_byte(stream, visited_labels)
            left = _one(_read_expressions(stream, visited_labels, data, 0xa8))
            right = _one(_read_expressions(stream, visited_labels, data, 0xa7))

            if left[0] == 'data':
                assert right[0] in ('data', 'integer') # TODO support assigning strings
                _set_data_type(data, left[1][0][1], 'integer')

            if right[0] == 'data':
                assert left[0] in ('data', 'string', 'integer') # TODO support assigning strings
                if left[0] == 'string':
                    _set_data_type(data, right[1][0][1], 'string')
                else:
                    _set_data_type(data, right[1][0][1], 'integer')

            result.append(('ASSIGN', left, right))

        elif code == 0xb5:
            _read_byte(stream, visited_labels)
            result.append(('DPRINT', _read_expressions(stream, visited_labels, data, 0xa7)))

        elif code == 0xb9:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(4)]
            result.append(('NEW', *arguments))

        elif code == 0xba:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(4)]
            result.append(('DELETE', *arguments))

        elif code == 0xbe:
            _read_byte(stream, visited_labels)
            result.append(('INVENTORY', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xbf:
            _read_byte(stream, visited_labels)
            result.append(('PORTRAIT', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xc4:
            _read_byte(stream, visited_labels)
            result.append(('ADD_KARMA', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xc5:
            _read_byte(stream, visited_labels)
            result.append(('SUB_KARMA', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xc9:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(4)]
            if arguments[1][0] == 'data': # TODO probably typehint other instructions too.
                _set_data_type(data, arguments[1][1][0][1], 'integer')
            result.append(('GIVE', *arguments))

        elif code == 0xcb:
            _read_byte(stream, visited_labels)
            result.append('WAIT')

        elif code == 0xcd:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(2)]
            result.append(('WORKTYPE', *arguments))

        elif code == 0xd6:
            _read_byte(stream, visited_labels)
            result.append(('RESURRECT', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xd8:
            _read_byte(stream, visited_labels)
            result.append(('SETNAME', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xd9:
            _read_byte(stream, visited_labels)
            result.append(('HEAL', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xdb:
            _read_byte(stream, visited_labels)
            result.append(('CURE', _one(_read_expressions(stream, visited_labels, data, 0xa7))))

        elif code == 0xef:
            # TODO can't have nested keywords
            while (code := _peek_byte(stream)) == 0xef:
                _read_byte(stream, visited_labels)
                keywords = _read_string(stream, visited_labels, {0xf6})
                _read_byte(stream, visited_labels)
                sub_visited_labels = set()
                instructions = _read_instructions(stream, labels, sub_visited_labels, data, allow_solo_endif, allow_drop_esac, {0xef, 0xee})
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


def _format_expression(expression):
    if expression[0] in ('byte', 'word', 'dword', 'value'):
        return ' '.join(map(str, expression))

    else:
        arguments = []
        for argument in expression[1]:
            arguments.append(_format_expression(argument))

        return f'{expression[0]}({", ".join(arguments)})'


def _expand_instructions(original_label, instructions, labels):
    result = []
    for instruction in instructions:
        if instruction[0] == 'IF':
            result.append((instruction[0], _format_expression(instruction[1])))
            result.extend(instruction[2])
            if instruction[3]:
                result.append('ELSE')
                result.extend(instruction[3])
            result.append('ENDIF')

        elif instruction[0] == 'KEYWORDS':
            # FIXME nest in read, expand here, add esac
            result.append(instruction)

        else:
            result.append(instruction)

    yield original_label, result # FIXME get rid of original_label


def decode(raw_conversation):
    stream = io.BufferedReader(io.BytesIO(raw_conversation))
    result = {}
    labels = set()
    visited_labels = set()
    data = {}

    digest = hashlib.sha256(raw_conversation).hexdigest()

    allow_drop_esac = digest in (
        '57e9da766ab59e6022b3446805f98a93869505a21217595fd87a8ef91e00d634',
        '7e8924944c3a1a04c8311b0b7ceab5c255d916854a761431e8385f5645774eb0',
        '8464e3db9e7067ecb8c681f343377bbe208acc7a99cab0c333c22d1bdb65bb68',
        'e7bd3bf7f3d17519d53bbf02929a3fd05dc0600e9891dd21cb18be21f7117481',
        'd28ad8bf501c1a64aca497885364a71799cb68c30dbdade68524b1767e953773',
        'd8fd7702c0201cff8140b573ca59aa91bb65bc2e09370b5bcc1b51e278310020',
    )

    allow_solo_endif = digest == '85f1912ed262ba67a28fdff87c31575d6dd2cea0fbf431ef73e2be77d0958a0d'

    assert _read_byte(stream, visited_labels) == 0xff
    result['id'] = _read_byte(stream, visited_labels)
    result['name'] = _read_string(stream, visited_labels, {0xf1, 0xf3})
    result['f3-after-name'] = _check_byte(stream, visited_labels, 0xf3)

    assert _read_byte(stream, visited_labels) == 0xf1
    result['description'] = _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, allow_drop_esac, {0xf2, 0xf3})
    result['f3-after-description'] = _check_byte(stream, visited_labels, 0xf3)

    assert _read_byte(stream, visited_labels) == 0xf2
    blocks = {stream.tell(): _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, allow_drop_esac, {None})}

    while labels - visited_labels:
        label = next(iter(labels - visited_labels))
        stream.seek(label)
        blocks[label] = _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, allow_drop_esac, {None})
        # FIXME split code with label in the middle, sometimes in the middle of string

    result['interaction'] = {label: expanded for k, v in sorted(blocks.items()) for label, expanded in _expand_instructions(k, v, labels)}

    types = dict(sorted(data.items()))
    offsets = list(types)
    assert set(types.values()) <= {'integer', 'string'}

    result['data'] = {}
    result['end-of-list-marker'] = []
    result['no-trailing-byte'] = []
    for left, right in zip(offsets, offsets[1:] + [len(raw_conversation)]):
        stream.seek(left)
        if types[left] == 'integer':
            integers = []

            for _ in range(left, right, 2):
                if stream.tell() in visited_labels:
                    break
                if stream.tell() + 1 in visited_labels or stream.tell() + 1 == right:
                    result['no-trailing-byte'].append(left)
                    integers.append(_read_byte(stream, visited_labels))
                else:
                    integers.append(_read_word(stream, visited_labels))

            result['data'][left] = integers

        else:
            assert types[left] == 'string'
            strings = []
            string = bytearray()

            for _ in range(left, right):
                if stream.tell() in visited_labels:
                    break
                char = _read_char(stream, visited_labels)
                if char == b'\x00':
                    strings.append(string.decode('ascii'))
                    string = bytearray()
                else:
                    string.extend(char)

            if string:
                if string == b'\xb8':
                    result['end-of-list-marker'].append(left)
                else:
                    result['no-trailing-byte'].append(left)
                    strings.append(string.decode('ascii'))

            result['data'][left] = strings

    assert set(range(len(data))) - visited_labels == set()
    return result
