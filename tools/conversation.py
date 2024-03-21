import hashlib
import io
import textwrap


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
    result = bytearray()
    while _peek_byte(stream) not in end:
        result.append(_read_byte(stream, visited_labels))
    return result.decode('ascii')


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
    # TODO include this to _read_instructions call on the fly updating last_block
    branch_ended = False
    keywords_covered = set()
    for i in range(len(result)-1, -1, -1):
        if result[i] == 'BYE' or result[i][0] == 'JUMP':
            branch_ended = True
        elif result[i][0] == 'IF':
            # Ветка завершена если или до IF или после или в обеих ветках IF будет jump FIXME typos
            branch_ended = branch_ended or _is_ended(result[i][2]) and _is_ended(result[i][3])
        elif result[i][0] == 'CASE':
            # TODO support nested cases
            keywords = result[i][1].split(',')
            if branch_ended:
                if '*' in keywords:
                    return True
                keywords_covered |= set(keywords)
            branch_ended = False
        elif result[i][0] == 'ASK':
            keywords_covered = set()
        elif result[i][0] == 'ASKC':
            if keywords_covered >= set(result[i][1]):
                return True
            keywords_covered = set()
    return branch_ended
    # TODO надо проходить не в обратном порядке, а по тому пути (по возможным путям) по которому мы пришли из заданной точки. Может быть и как попало ок.


def _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, end):
    result = []

    all_instructions = {
        0x9c, 0x9e,
        0xa1, 0xa4, 0xa5, 0xa6,
        0xb0, 0xb5, 0xb6, 0xb9, 0xba, 0xbe, 0xbf,
        0xc4, 0xc5, 0xc9, 0xcb, 0xcd,
        0xd6, 0xd8, 0xd9, 0xdb,
        0xee, 0xef,
        0xf3, 0xf7, 0xf8, 0xf9, 0xfb, 0xfc,
    }
    if allow_solo_endif:
        all_instructions.add(0xa2)

    # TODO there are more instructions in the game
    while (code := _peek_byte(stream)) not in end and stream.tell() not in visited_labels:
        offset = stream.tell()
        # FIXME linearize and get rid of end
        # FIXME get rid of expand
        # FIXME dont save to result, save to interaction
        # FIXME merge data with interaction
        # FIXME read till the end for look , add ff, f1, f2, f3 manually
        # FIXME get rid of json, make it custom

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
            instructions = _read_instructions(stream, labels, sub_visited_labels, data, allow_solo_endif, {0xa2, 0xa3})
            visited_labels |= sub_visited_labels
            if _read_byte(stream, visited_labels) == 0xa3:
                sub_visited_labels = set() # FIXME does it help?
                alternative_instructions = _read_instructions(stream, labels, sub_visited_labels, data, allow_solo_endif, {0xa2})
                visited_labels |= sub_visited_labels
                _read_byte(stream, visited_labels)
            else:
                alternative_instructions = tuple()
            result.append(('IF', expression, instructions, alternative_instructions))

        elif code == 0xa2 and allow_solo_endif:
            # Happens once, with Valkadesh.
            _read_byte(stream, visited_labels)
            result.append('SOLO_ENDIF')

        elif code == 0xb0:
            _read_byte(stream, visited_labels)
            label = _read_dword(stream, visited_labels)
            labels.add(label)
            result.append(('JUMP', label))

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

        elif code == 0xee:
            _read_byte(stream, visited_labels)
            # May be absent
            result.append('ESAC')

        elif code == 0xef:
            # TODO can't have nested keywords
            _read_byte(stream, visited_labels)
            keywords = _read_string(stream, visited_labels, {0xf6})
            _read_byte(stream, visited_labels)
            result.append(('CASE', keywords))

        elif code == 0xf7:
            _read_byte(stream, visited_labels)
            result.append('ASK')

        elif code == 0xf8:
            _read_byte(stream, visited_labels)
            result.append(('ASKC', _read_string(stream, visited_labels, end | all_instructions)))

        elif code == 0xf9:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            assert _read_byte(stream, visited_labels) == 0xb3
            result.append(('INPUTSTR', number))

        elif code == 0xfb:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            assert _read_byte(stream, visited_labels) == 0xb2
            result.append(('INPUT', number))

        elif code == 0xf3:
            _read_byte(stream, visited_labels)
            result.append('F3')

        elif code == 0xfc:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            assert _read_byte(stream, visited_labels) == 0xb2
            result.append(('INPUTNUM', number))

        else:
            result.append(('PRINT', _read_string(stream, visited_labels, end | all_instructions)))

        # FIXME move to main while
        if _peek_byte(stream) is None or _is_ended(result) and None in end:
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
            result.append((instruction[0], instruction[1]))
            result.extend(instruction[2])
            if instruction[3]:
                result.append('ELSE')
                result.extend(instruction[3])
            result.append('ENDIF')

        else:
            result.append(instruction)

    yield original_label, result # FIXME get rid of original_label


def _format_string(string):
    escaping = str.maketrans({'\\': '\\\\', '"': '\\"', '\n': '\\n'})
    return string.translate(escaping)


def _format_instructions(instructions):
    def empty_prefix_line():
        if result and result[-1] != '':
            result.append('')

    result = []
    for instruction in instructions:
        # FIXME string escaping
        if instruction[0] == 'IF':
            empty_prefix_line()
            result.append(f'if {_format_expression(instruction[1])}:')
            #result.extend(textwrap.wrap(f'if {_format_expression(instruction[1])}:', subsequent_indent='    '))  # FIXME

        # FIXME rename
        elif instruction[0] == 'ASKC':
            empty_prefix_line()
            result.append(f'askc("{_format_string(instruction[1])}")')

        elif instruction[0] == 'PRINT':
            # FIXME smarter, with spaces at starts of lines, use minus all indent and print ?
            lines = textwrap.wrap(instruction[1], expand_tabs=False, replace_whitespace=False, drop_whitespace=False)
            assert ''.join(lines) == instruction[1]
            for line in lines:
                result.append(f'print("{_format_string(line)}")')

        elif instruction == 'ASK':
            empty_prefix_line()
            result.append(f'ask()')

        elif instruction[0] == 'CASE':
            result.append(f'case "{_format_string(instruction[1])}":')

        elif instruction[0] == 'ASSIGN':
            result.append(f'{_format_expression(instruction[1])} = {_format_expression(instruction[2])}')

        elif instruction == 'ESAC':
            empty_prefix_line()
            result.append('esac')
            result.append('')

        elif instruction == 'ENDIF':
            empty_prefix_line()
            result.append('endif')
            result.append('')

        elif instruction == 'F3':
            empty_prefix_line()
            result.append('f3()')

        elif instruction == 'WAIT':
            result.append('wait()')
            result.append('')

        elif instruction == 'ELSE':
            empty_prefix_line()
            result.append('else:')

        elif instruction == 'BYE':
            result.append('bye()')
            result.append('')

        elif instruction[0] == 'JUMP':
            result.append(f'jump {instruction[1]}')
            result.append('')

        else:
            result.append(str(instruction))

    if result and result[-1] == '':
        del result[-1]

    return [f'    {line}' if line else '' for line in result]


def decode(raw_conversation):
    stream = io.BufferedReader(io.BytesIO(raw_conversation))
    result = []
    labels = set()
    visited_labels = set()
    data = {}

    digest = hashlib.sha256(raw_conversation).hexdigest()

    allow_solo_endif = digest == '85f1912ed262ba67a28fdff87c31575d6dd2cea0fbf431ef73e2be77d0958a0d'

    assert _read_byte(stream, visited_labels) == 0xff
    result.append(f'id({_read_byte(stream, visited_labels)})')

    name = _read_string(stream, visited_labels, {0xf1, 0xf3})
    if name == 'Dr_ Cat':
        name = 'Dr. Cat'
    elif name == 'ed':
        name = 'Ed'
    result.append(f'name("{_format_string(name)}")')

    if _check_byte(stream, visited_labels, 0xf3):
        result.append('')
        result.append('f3()')

    result.append('')
    assert _read_byte(stream, visited_labels) == 0xf1
    result.append('description:')
    result.extend(_format_instructions(_read_instructions(stream, labels, visited_labels, data, allow_solo_endif, {0xf2})))

    result.append('')
    assert _read_byte(stream, visited_labels) == 0xf2
    result.append('interaction:')
    start = stream.tell()

    blocks = {stream.tell(): _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, {None})}

    # TODO support jumps to the middle of unknown blocks with branches
    # FIXME at least detect it
    while labels - visited_labels:
        label = next(iter(labels - visited_labels))
        stream.seek(label)
        blocks[label] = _read_instructions(stream, labels, visited_labels, data, allow_solo_endif, {None})
        # FIXME split code with label in the middle, sometimes in the middle of string

    types = dict(sorted(data.items()))
    offsets = list(types)
    assert set(types.values()) <= {'integer', 'string'}

    for left, right in zip(offsets, offsets[1:] + [len(raw_conversation)]):
        stream.seek(left)
        if types[left] == 'integer':
            integers = []

            assert left not in blocks
            blocks[left] = [['INTEGERS', integers]]

            for _ in range(left, right, 2):
                if stream.tell() in visited_labels:
                    break
                if stream.tell() + 1 in visited_labels or stream.tell() + 1 == right:
                    integers.append(_read_byte(stream, visited_labels))
                    blocks[left].append('no-trailing-byte')
                else:
                    integers.append(_read_word(stream, visited_labels))

        else:
            assert types[left] == 'string'
            strings = []
            string = bytearray()

            assert left not in blocks
            blocks[left] = [['STRINGS', strings]]

            for _ in range(left, right):
                if stream.tell() in visited_labels:
                    break
                byte = _read_byte(stream, visited_labels)
                if not byte:
                    strings.append(string.decode('ascii'))
                    string = bytearray()
                else:
                    string.append(byte)

            if string:
                if string == b'\xb8':
                    blocks[left].append('end-of-list-marker')
                else:
                    strings.append(string.decode('ascii'))
                    blocks[left].append('no-trailing-byte')

    assert set(range(len(data))) - visited_labels == set()

    for k, v in sorted(blocks.items()):
        for label, expanded in _expand_instructions(k, v, labels):
            if label != start: # FIXME substitute jumps
                result.append('')
                result.append(f'{label}:')
            result.extend(_format_instructions(expanded))

    return ''.join((line + '\n' for line in result))
