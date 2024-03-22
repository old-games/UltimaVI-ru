import io
import textwrap


def _read_char(stream, visited_labels):
    visited_labels.add(stream.tell())
    char = stream.read(1)
    assert char
    return char


def _peek_byte(stream):
    data = stream.peek(1)[:1]
    return int.from_bytes(data, 'little') if len(data) == 1 else None


def _peek_word(stream):
    data = stream.peek(2)[:2]
    return int.from_bytes(data, 'little') if len(data) == 2 else None


def _read_byte(stream, visited_labels):
    data = stream.read(1)
    assert len(data) == 1
    visited_labels |= set(range(stream.tell()-1, stream.tell()))
    return int.from_bytes(data, 'little')


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


def _is_text(byte):
    return byte in (9, 0x0a) or 0x20 <= byte < 0x80


def _read_string(stream, visited_labels, end):
    result = bytearray()
    while _peek_byte(stream) not in end:
        byte = _read_byte(stream, visited_labels)
        assert _is_text(byte)
        result.append(byte)
    return result.decode('ascii')


def _try_read_string(stream, end):
    result = bytearray()
    start = stream.tell()
    while _peek_byte(stream) not in end:
        byte = _read_byte(stream, set())
        if not _is_text(byte):
            stream.seek(start)
            return None
        result.append(byte)
    stream.seek(start)
    return result.decode('ascii')


def _set_data_type(data, offset, type):
    assert data[offset] in (None, type)
    # FIXME Can also collect and check afterwards.
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


def _add_branch_ended(branches_ended, stack, choices, keywords):
    if stack:
        parent = stack[:-1]

        def add_parent():
            _add_branch_ended(branches_ended, parent, choices, keywords)

        if stack[-1][0] == 'else' and branches_ended[(*parent, ('if', stack[-1][1]))]:
            add_parent()

        elif stack[-1][0] == 'case':
            if '*' in keywords[tuple(stack)]:
                add_parent()

            elif choices.get(tuple(parent)) is not None: # Mondain, no ask, no tell.
                choices[tuple(parent)] -= keywords[tuple(stack)]
                if not choices[tuple(parent)]:
                    add_parent()

    branches_ended[tuple(stack)] = True


def _read_instructions(stream, result, labels, visited_labels, unreachable_labels, error_labels, data, end):
    all_instructions = {
        0x9c, 0x9e,
        0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6,
        0xb0, 0xb5, 0xb6, 0xb9, 0xb9, 0xba, 0xbe, 0xbf,
        0xc4, 0xc5, 0xc9, 0xcb, 0xcd,
        0xd6, 0xd8, 0xd9, 0xdb,
        0xee, 0xef,
        0xf3, 0xf7, 0xf8, 0xf9, 0xfb, 0xfc,
    }
    # TODO there are more instructions in the game

    stack = []
    branches_ended = {tuple(): False}
    choices = {}
    keywords = {}
    while (
        (code := _peek_byte(stream)) not in end
        and code is not None
        and ((offset := stream.tell()) not in data or unreachable_labels is None)
        and (None not in end or not branches_ended[tuple()]) # Выходим, если читать больше нечего или не ждём окончания определённого блока.
    ):
        assert offset not in data
        # FIXME get rid of end
        # FIXME dont save to result, save to interaction
        # FIXME merge data with interaction
        # FIXME read till the end for look , add ff, f1, f2, f3 as regular instructions
        # FIXME f1, f2 are stop operators
        # TODO расклеить слова
        # TODO проверить что инструкции не налезают одна на другую

        if offset in visited_labels:
            # Необходимо прочитать код повторно, если мы прыгнули на новую метку, контекст может закончиться раньше или позже, чем в прошлый раз.
            if unreachable_labels is not None and offset not in unreachable_labels:
                unreachable_labels = None
            # FIXME assert this is not array
            # FIXME quit if we already came here from start point or with same stack
            # FIXME чекнуть после всего этого может эвристики внизу больше не нужны

        # FIXME чекать что записываем в result то же самое

        if code == 0x9c:
            _read_byte(stream, visited_labels)
            result[offset] = 'HORSE', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0x9e:
            _read_byte(stream, visited_labels)
            result[offset] = 'SLEEP',

        elif code == 0xa1:
            _read_byte(stream, visited_labels)
            expression = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            result[offset] = 'IF', expression
            stack.append(('if', stream.tell()))
            branches_ended[tuple(stack)] = False

        elif code == 0xa2:
            _read_byte(stream, visited_labels)
            result[offset] = 'ENDIF',
            if stack:
                assert stack[-1][0] in ('if', 'else')
                del stack[-1]

        elif code == 0xa3:
            _read_byte(stream, visited_labels)
            result[offset] = 'ELSE',
            flow, start = stack.pop()
            assert flow == 'if'
            stack.append(('else', start))
            branches_ended[tuple(stack)] = False

        elif code == 0xb0:
            _read_byte(stream, visited_labels)
            label = _read_dword(stream, visited_labels)
            labels.add(label)
            result[offset] = 'JUMP', label
            _add_branch_ended(branches_ended, stack, choices, keywords)

        elif code == 0xb6:
            _read_byte(stream, visited_labels)
            result[offset] = 'BYE',
            _add_branch_ended(branches_ended, stack, choices, keywords)

        elif code == 0xa4:
            _read_byte(stream, visited_labels)
            left = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            right = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            result[offset] = 'SETF', left, right

        elif code == 0xa5:
            _read_byte(stream, visited_labels)
            left = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            right = _one(_read_expressions(stream, visited_labels, data, 0xa7))
            result[offset] = 'CLEARF', left, right

        elif code == 0xa6:
            # TODO support packing and unpacking
            # TODO support assigning strings
            _read_byte(stream, visited_labels)
            left = _one(_read_expressions(stream, visited_labels, data, 0xa8))
            right = _one(_read_expressions(stream, visited_labels, data, 0xa7))

            if left[0] == 'data':
                assert right[0] in ('data', 'integer')
                _set_data_type(data, left[1][0][1], 'integer')

            if right[0] == 'data':
                assert left[0] in ('data', 'string', 'integer')
                if left[0] == 'string':
                    _set_data_type(data, right[1][0][1], 'string')
                else:
                    _set_data_type(data, right[1][0][1], 'integer')

            result[offset] = 'ASSIGN', left, right

        elif code == 0xb5:
            _read_byte(stream, visited_labels)
            index, strings = _read_expressions(stream, visited_labels, data, 0xa7)
            assert strings[0] == 'dword'
            data.setdefault(strings[1], None)
            _set_data_type(data, strings[1], 'string')
            result[offset] = 'DPRINT', strings, index

        elif code == 0xb8:
            _read_byte(stream, visited_labels)
            result[offset] = 'ENDOFLIST',

        elif code == 0xb9:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(4)]
            result[offset] = 'NEW', *arguments

        elif code == 0xba:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(4)]
            result[offset] = 'DELETE', *arguments

        elif code == 0xbe:
            _read_byte(stream, visited_labels)
            result[offset] = 'INVENTORY', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xbf:
            _read_byte(stream, visited_labels)
            result[offset] = 'PORTRAIT', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xc4:
            _read_byte(stream, visited_labels)
            result[offset] = 'ADD_KARMA', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xc5:
            _read_byte(stream, visited_labels)
            result[offset] = 'SUB_KARMA', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xc9:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(4)]

            if arguments[1][0] == 'data': # TODO probably typehint other instructions too.
                _set_data_type(data, arguments[1][1][0][1], 'integer')

            result[offset] = 'GIVE', *arguments

        elif code == 0xcb:
            _read_byte(stream, visited_labels)
            result[offset] = 'WAIT',

        elif code == 0xcd:
            _read_byte(stream, visited_labels)
            arguments = [_one(_read_expressions(stream, visited_labels, data, 0xa7)) for _ in range(2)]
            result[offset] = 'WORKTYPE', *arguments

        elif code == 0xd6:
            _read_byte(stream, visited_labels)
            result[offset] = 'RESURRECT', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xd8:
            _read_byte(stream, visited_labels)
            result[offset] = 'SETNAME', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xd9:
            _read_byte(stream, visited_labels)
            result[offset] = 'HEAL', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xdb:
            _read_byte(stream, visited_labels)
            result[offset] = 'CURE', _one(_read_expressions(stream, visited_labels, data, 0xa7))

        elif code == 0xee:
            # May be absent.
            _read_byte(stream, visited_labels)
            if stack and stack[-1][0] == 'case':
                del stack[-1]
            result[offset] = 'ESAC',

        elif code == 0xef:
            # TODO can't have nested keywords
            _read_byte(stream, visited_labels)
            argument = _read_string(stream, visited_labels, {0xf6}).split(',')
            _read_byte(stream, visited_labels)
            result[offset] = 'CASE', argument
            # TODO вложенные ask в case ? leak choices to parent
            if stack and stack[-1][0] == 'case':
                del stack[-1]
            stack.append(('case', stream.tell()))
            keywords[tuple(stack)] = set(argument)
            branches_ended[tuple(stack)] = False

        elif code == 0xf7:
            _read_byte(stream, visited_labels)
            result[offset] = 'ASK',
            choices[tuple(stack)] = None

        elif code == 0xf8:
            _read_byte(stream, visited_labels)
            argument = _read_string(stream, visited_labels, end | all_instructions)
            result[offset] = 'CHOICE', argument
            choices[tuple(stack)] = set(argument)

        elif code == 0xf9:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            assert _read_byte(stream, visited_labels) == 0xb3
            result[offset] = 'INPUTSTR', number

        elif code == 0xfb:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            assert _read_byte(stream, visited_labels) == 0xb2
            result[offset] = 'INPUT', number

        elif code == 0xf3:
            _read_byte(stream, visited_labels)
            result[offset] = 'F3',

        elif code == 0xfc:
            _read_byte(stream, visited_labels)
            number = _read_byte(stream, visited_labels)
            assert _read_byte(stream, visited_labels) == 0xb2
            result[offset] = 'INPUTNUM', number

        elif _try_read_string(stream, end | all_instructions):
            result[offset] = 'PRINT', _read_string(stream, visited_labels, end | all_instructions)

        else:
            assert unreachable_labels is not None
            assert error_labels is not None
            error_labels.add(offset)
            break

        if unreachable_labels is not None:
            unreachable_labels.add(offset)


def _read_integers(stream, result, visited_labels, unreachable_labels, end):
    integers = []
    comments = []

    offset = stream.tell()
    assert offset not in result
    result[offset] = 'INTEGERS', integers, comments

    for offset in range(offset, end, 2):
        if offset in visited_labels or _peek_byte(stream) is None:
            break

        if offset + 1 in visited_labels or offset + 1 == end or _peek_word(stream) is None:
            integers.append(_read_byte(stream, visited_labels))
            comments.append('no-trailing-byte')
            break

        else:
            integers.append(_read_word(stream, visited_labels))

    if unreachable_labels is not None:
        comments.append('unused')


def _read_strings(stream, result, visited_labels, unreachable_labels, end):
    strings = []
    comments = []
    string = bytearray()

    offset = stream.tell()
    assert offset not in result
    result[offset] = 'STRINGS', strings, comments

    for offset in range(offset, end):
        if offset in visited_labels:
            break

        # FIXME reuse _try_read_string? without overlap
        if (byte := _peek_byte(stream)) and not _is_text(byte):
            break

        _read_byte(stream, visited_labels)

        if not byte:
            strings.append(string.decode('ascii'))
            string = bytearray()

        else:
            string.append(byte)

    if string:
        strings.append(string.decode('ascii'))
        comments.append('no-trailing-byte')


def _format_expression(expression):
    if expression[0] in ('byte', 'word', 'dword', 'value'):
        return ' '.join(map(str, expression))

    else:
        arguments = []
        for argument in expression[1]:
            arguments.append(_format_expression(argument))

        return f'{expression[0]}({", ".join(arguments)})'


def _format_string(string):
    escaping = str.maketrans({'\\': '\\\\', "'": "\\'", '\n': '\\n', '\t': '\\t'})
    return f"'{string.translate(escaping)}'"


def _format_instructions(instructions, labels, unreachable_labels, description, interaction):
    levels = [None]
    last_level = 0
    result = []

    def increase_level(why):
        levels.append(why)

    def decrease_level(why):
        if why != 'case' or levels[-1] == 'case':
            if len(levels) == 1:
                append()
                append('// Wrong flow!')
            else:
                del levels[-1]

    def append(line=None, force_level=None):
        nonlocal last_level
        if line:
            last_level = len(levels) if force_level is None else force_level
            result.append(f'{" "*last_level*4}{line}')
        else:
            result.append('')

    def empty_prefix_line():
        if result and result[-1] != '' and last_level >= len(levels):
            append()

    def remove_empty_line():
        if result and result[-1] == '':
            del result[-1]

    for label, instruction in instructions:
        if label == description:
            empty_prefix_line()
            append('description:', force_level=0)

        elif label == interaction:
            empty_prefix_line()
            append('interaction:', force_level=0)

        elif label in labels:
            empty_prefix_line()
            append(f'label_{label}:', force_level=0)

        if label in unreachable_labels and instruction[0] not in ('ENDOFLIST', 'ESAC', 'ELSE', 'ENDIF'):
            empty_prefix_line()
            append('// Unreachable code!')
            # TODO mark each line

        if instruction[0] == 'IF':
            empty_prefix_line()
            append(f'if {_format_expression(instruction[1])}:')
            #result.extend(textwrap.wrap(f'if {_format_expression(instruction[1])}:', subsequent_indent='    '))  # FIXME
            increase_level('if')

        # FIXME rename
        elif instruction[0] == 'CHOICE':
            empty_prefix_line()
            append(f'choice({_format_string(instruction[1])})')

        elif instruction[0] == 'PRINT':
            # FIXME smarter, with spaces at starts of lines, use minus all indent and print ?
            lines = textwrap.wrap(instruction[1], expand_tabs=False, replace_whitespace=False, drop_whitespace=False)
            assert ''.join(lines) == instruction[1]
            for line in lines:
                append(f'print({_format_string(line)})')

        elif instruction[0] == 'ASK':
            empty_prefix_line()
            append('ask()')

        elif instruction[0] == 'ENDOFLIST':
            append('endOfList()')
            empty_prefix_line()

        elif instruction[0] == 'CASE':
            empty_prefix_line()
            decrease_level('case')
            for case in sorted(instruction[1]):
                append(f'case {_format_string(case)}:')
            increase_level('case')

        elif instruction[0] == 'ASSIGN':
            append(f'{_format_expression(instruction[1])} = {_format_expression(instruction[2])}')

        elif instruction[0] == 'ESAC':
            remove_empty_line()
            decrease_level('esac')
            append('esac')
            append()

        elif instruction[0] == 'ENDIF':
            remove_empty_line()
            decrease_level('if')
            append('fi')
            append()

        elif instruction[0] == 'F3':
            empty_prefix_line()
            append('f3()')

        elif instruction[0] == 'WAIT':
            append('wait()')
            append()

        elif instruction[0] == 'ELSE':
            empty_prefix_line()
            decrease_level('if')
            append('else:')
            increase_level('if')

        elif instruction[0] == 'BYE':
            append('bye()')
            append()

        elif instruction[0] == 'SLEEP':
            append('sleep()')
            append()

        elif instruction[0] in ('INTEGERS', 'STRINGS'):
            empty_prefix_line()
            if instruction[2][-1:] == ['unused']:
                name = 'unused'
                del instruction[2][-1]
            else:
                name = 'integers' if instruction[0] == 'INTEGERS' else 'strings'
            append(f'{name}_{label} = [', force_level=0)
            values = []
            for item in instruction[1]:
                values.append(str(item) if instruction[0] == 'INTEGERS' else _format_string(item))
            max_size = max(map(len, values)) + 1
            for index, value in enumerate(values):
                # FIXME переделать названия в выражениях
                # FIXME pad numbers to right
                append(f'{value},'.ljust(max_size) + f' // {index}', force_level=1)
            append(f']', force_level=0)
            append()

        elif instruction[0] == 'JUMP':
            if instruction[1] == description:
                append(f'jump description')
            elif instruction[1] == interaction:
                append(f'jump interaction')
            else:
                append(f'jump label_{instruction[1]}')
            append()

        else:
            append(str(instruction))

    if result and result[-1] == '':
        del result[-1]

    return result


def decode(conversation):
    stream = io.BufferedReader(io.BytesIO(conversation))
    result = []
    blocks = {}
    labels = set()
    visited_labels = set()
    data = {}

    assert _read_byte(stream, visited_labels) == 0xff
    result.append(f'id({_read_byte(stream, visited_labels)})')

    name = _read_string(stream, visited_labels, {0xf1, 0xf3})
    if name == 'Dr_ Cat':
        name = 'Dr. Cat'
    elif name == 'ed':
        name = 'Ed'
    result.append(f'name({_format_string(name)})')

    if _check_byte(stream, visited_labels, 0xf3):
        result.append('')
        result.append('f3()')

    result.append('')
    assert _read_byte(stream, visited_labels) == 0xf1
    description = stream.tell()
    _read_instructions(stream, blocks, labels, visited_labels, None, None, data, {0xf2})

    assert _read_byte(stream, visited_labels) == 0xf2
    interaction = stream.tell()
    _read_instructions(stream, blocks, labels, visited_labels, None, None, data, {None})

    while labels - visited_labels:
        label = next(iter(labels - visited_labels))
        stream.seek(label)
        _read_instructions(stream, blocks, labels, visited_labels, None, None, data, {None})

    visited_data = set()
    unreachable_labels = set()
    error_labels = set()
    while set(data) != visited_data or set(range(len(conversation))) != visited_labels | error_labels:
        while new_data := set(data) - visited_data:
            types = dict(sorted(((label, data[label]) for label in new_data)))
            offsets = list(types)
            assert set(types.values()) <= {'integer', 'string'}

            for left, right in zip(offsets, offsets[1:] + [len(conversation)]):
                stream.seek(left)
                visited_data.add(left)
                if types[left] == 'integer':
                    _read_integers(stream, blocks, visited_labels, None, right)

                else:
                    assert types[left] == 'string'
                    _read_strings(stream, blocks, visited_labels, None, right)

        # FIXME set(range(len(conversation))) to var
        while remaining_labels := set(range(len(conversation))) - visited_labels - error_labels:
            label = min(remaining_labels)
            stream.seek(label)
            # TODO ссылки могут не работать, чекнуть
            # TODO данные могут не работать, чекнуть
            _read_instructions(stream, blocks, labels, visited_labels, unreachable_labels, error_labels, data, {None})

    # FIXME set(range(len(conversation))) to var
    while remaining_labels := set(range(len(conversation))) - visited_labels:
        label = min(remaining_labels)
        stream.seek(label)
        _read_integers(stream, blocks, visited_labels, unreachable_labels, len(conversation))

    assert set(range(len(conversation))) - visited_labels == set()

    result.extend(_format_instructions(sorted(blocks.items()), labels, unreachable_labels, description, interaction))

    return ''.join((line + '\n' for line in result))
