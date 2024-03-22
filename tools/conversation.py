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
    while (byte := _peek_byte(stream)) is not None and byte not in end:
        _read_byte(stream, visited_labels)
        assert _is_text(byte)
        result.append(byte)
    return result.decode('ascii')


def _try_read_string(stream, end):
    result = bytearray()
    start = stream.tell()
    while (byte := _peek_byte(stream)) is not None and byte not in end:
        _read_byte(stream, set())
        if not _is_text(byte):
            stream.seek(start)
            return None
        result.append(byte)
    stream.seek(start)
    return result.decode('ascii')


def decode(conversation):
    def read_integers(unused, end):
        integers = []
        comments = []

        offset = stream.tell()
        assert offset not in blocks
        blocks[offset] = 'INTEGERS', integers, comments

        for offset in range(offset, end, 2):
            if offset in visited_labels or _peek_byte(stream) is None:
                break

            if offset + 1 in visited_labels or offset + 1 == end or _peek_word(stream) is None:
                integers.append(_read_byte(stream, visited_labels))
                comments.append('no-trailing-byte')
                break

            else:
                integers.append(_read_word(stream, visited_labels))

        if unused:
            comments.append('unused')

    def read_strings(end):
        strings = []
        comments = []
        string = bytearray()

        offset = stream.tell()
        assert offset not in blocks
        blocks[offset] = 'STRINGS', strings, comments

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

    def read_instructions(unreachable):
        all_instructions = {
            0x9c, 0x9e,
            0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6,
            0xb0, 0xb5, 0xb6, 0xb9, 0xb9, 0xba, 0xbe, 0xbf,
            0xc4, 0xc5, 0xc9, 0xcb, 0xcd,
            0xd6, 0xd8, 0xd9, 0xdb,
            0xee, 0xef,
            0xf1, 0xf2, 0xf3, 0xf7, 0xf8, 0xf9, 0xfb, 0xfc,
        }
        # TODO there are more instructions in the game

        def add(*args):
            blocks[offset] = code, stream.tell() - offset, *args

        def add_branch_ended(branches_ended, stack, choices, keywords):
            if stack:
                parent = stack[:-1]
                def add_parent():
                    add_branch_ended(branches_ended, parent, choices, keywords)
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

        def one(collection):
            assert len(collection) == 1
            return collection[0]

        def set_data_type(offset, type):
            assert data[offset] in (None, type)
            # FIXME Can also collect and check afterwards.
            data[offset] = type

        def read_expressions(end):
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
                            set_data_type(argument[1][0][1], 'integer')

                    return (operator, arguments)

            expressions = []
            while parts:
                expressions.append(process_parts(parts, data))

            return expressions

        stack = []
        branches_ended = {tuple(): False}
        choices = {}
        keywords = {}

        # Выходим, если читать больше нечего или не ждём окончания определённого блока или встретились с данными в unreachable коде.
        while (code := _peek_byte(stream)) is not None and ((offset := stream.tell()) not in data or not unreachable) and not branches_ended[tuple()]:
            # Проверим, что не встречаемся с данными в обычном коде.
            assert offset not in data

            # TODO расклеить слова
            # TODO проверить что инструкции не налезают одна на другую

            if offset in visited_labels:
                # Необходимо прочитать код повторно, если мы прыгнули на новую метку, контекст может закончиться раньше или позже, чем в прошлый раз.
                if unreachable and offset not in unreachable_labels:
                    unreachable = False
                # FIXME assert this is not array
                # FIXME quit if we already came here from start point or with same stack
                # FIXME чекнуть после всего этого может эвристики внизу больше не нужны

            # FIXME чекать что записываем в result тe же самые инструкции (в add)

            if code == 0x9c:
                _read_byte(stream, visited_labels)
                blocks[offset] = code, one(read_expressions(0xa7))

            elif code == 0x9e:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'SLEEP',

            elif code == 0xa1:
                _read_byte(stream, visited_labels)
                expression = one(read_expressions(0xa7))
                blocks[offset] = 'IF', expression
                stack.append(('if', stream.tell()))
                branches_ended[tuple(stack)] = False

            elif code == 0xa2:
                _read_byte(stream, visited_labels)
                if stack:
                    assert stack[-1][0] in ('if', 'else')
                    del stack[-1]
                add()

            elif code == 0xa3:
                _read_byte(stream, visited_labels)
                flow, start = stack.pop()
                assert flow == 'if'
                stack.append(('else', start))
                branches_ended[tuple(stack)] = False
                add()

            elif code == 0xb0:
                _read_byte(stream, visited_labels)
                label = _read_dword(stream, visited_labels)
                labels.add(label)
                blocks[offset] = 'JUMP', label
                add_branch_ended(branches_ended, stack, choices, keywords)

            elif code == 0xb6:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'BYE',
                add_branch_ended(branches_ended, stack, choices, keywords)

            elif code == 0xa4:
                _read_byte(stream, visited_labels)
                left = one(read_expressions(0xa7))
                right = one(read_expressions(0xa7))
                blocks[offset] = 'SETF', left, right

            elif code == 0xa5:
                _read_byte(stream, visited_labels)
                left = one(read_expressions(0xa7))
                right = one(read_expressions(0xa7))
                blocks[offset] = 'CLEARF', left, right

            elif code == 0xa6:
                # TODO support packing and unpacking
                # TODO support assigning strings
                _read_byte(stream, visited_labels)
                left = one(read_expressions(0xa8))
                right = one(read_expressions(0xa7))

                if left[0] == 'data':
                    assert right[0] in ('data', 'integer')
                    set_data_type(left[1][0][1], 'integer')

                if right[0] == 'data':
                    assert left[0] in ('data', 'string', 'integer')
                    if left[0] == 'string':
                        set_data_type(right[1][0][1], 'string')
                    else:
                        set_data_type(right[1][0][1], 'integer')

                blocks[offset] = code, left, right

            elif code == 0xb5:
                _read_byte(stream, visited_labels)
                index, strings = read_expressions(0xa7)
                assert strings[0] == 'dword'
                data.setdefault(strings[1], None)
                set_data_type(strings[1], 'string')
                blocks[offset] = 'DPRINT', strings, index

            elif code == 0xb8:
                _read_byte(stream, visited_labels)
                blocks[offset] = code,

            elif code == 0xb9:
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(4)]
                blocks[offset] = 'NEW', *arguments

            elif code == 0xba:
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(4)]
                blocks[offset] = 'DELETE', *arguments

            elif code == 0xbe:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'INVENTORY', one(read_expressions(0xa7))

            elif code == 0xbf:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'PORTRAIT', one(read_expressions(0xa7))

            elif code == 0xc4:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'ADD_KARMA', one(read_expressions(0xa7))

            elif code == 0xc5:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'SUB_KARMA', one(read_expressions(0xa7))

            elif code == 0xc9:
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(4)]

                if arguments[1][0] == 'data': # TODO probably typehint other instructions too.
                    set_data_type(arguments[1][1][0][1], 'integer')

                blocks[offset] = 'GIVE', *arguments

            elif code == 0xcb:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'WAIT',

            elif code == 0xcd:
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(2)]
                blocks[offset] = 'WORKTYPE', *arguments

            elif code == 0xd6:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'RESURRECT', one(read_expressions(0xa7))

            elif code == 0xd8:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'SETNAME', one(read_expressions(0xa7))

            elif code == 0xd9:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'HEAL', one(read_expressions(0xa7))

            elif code == 0xdb:
                _read_byte(stream, visited_labels)
                blocks[offset] = 'CURE', one(read_expressions(0xa7))

            elif code == 0xee:
                # May be absent.
                _read_byte(stream, visited_labels)
                if stack and stack[-1][0] == 'case':
                    del stack[-1]
                add()

            elif code == 0xef:
                # TODO can't have nested keywords
                _read_byte(stream, visited_labels)
                argument = _read_string(stream, visited_labels, {0xf6}).split(',')
                _read_byte(stream, visited_labels)
                blocks[offset] = 0xef, argument
                # TODO вложенные ask в case ? leak choices to parent
                if stack and stack[-1][0] == 'case':
                    del stack[-1]
                stack.append(('case', stream.tell()))
                keywords[tuple(stack)] = set(argument)
                branches_ended[tuple(stack)] = False

            elif code == 0xf2:
                _read_byte(stream, visited_labels)
                special_labels[stream.tell()] = 'interaction'

            elif code == 0xf1:
                _read_byte(stream, visited_labels)
                special_labels[stream.tell()] = 'description'

            elif code == 0xf7:
                _read_byte(stream, visited_labels)
                blocks[offset] = code,
                choices[tuple(stack)] = None

            elif code == 0xf8:
                _read_byte(stream, visited_labels)
                argument = _read_string(stream, visited_labels, all_instructions)
                blocks[offset] = code, argument
                choices[tuple(stack)] = set(argument)

            elif code == 0xf9:
                _read_byte(stream, visited_labels)
                number = _read_byte(stream, visited_labels)
                assert _read_byte(stream, visited_labels) == 0xb3
                blocks[offset] = 'INPUTSTR', number

            elif code == 0xfb:
                _read_byte(stream, visited_labels)
                number = _read_byte(stream, visited_labels)
                assert _read_byte(stream, visited_labels) == 0xb2
                blocks[offset] = 'INPUT', number

            elif code == 0xf3:
                _read_byte(stream, visited_labels)
                add()

            elif code == 0xfc:
                _read_byte(stream, visited_labels)
                number = _read_byte(stream, visited_labels)
                assert _read_byte(stream, visited_labels) == 0xb2
                blocks[offset] = 'INPUTNUM', number

            elif code == 0xff:
                _read_byte(stream, visited_labels)
                blocks[offset] = 0xff, _read_byte(stream, visited_labels), _read_string(stream, visited_labels, {0xf1, 0xf3})

            elif _try_read_string(stream, all_instructions):
                blocks[offset] = 'PRINT', _read_string(stream, visited_labels, all_instructions)

            else:
                assert unreachable
                error_labels.add(offset)
                break

            if unreachable:
                unreachable_labels.add(offset)

    def format_instructions():
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

        def format_string(string):
            escaping = str.maketrans({'\\': '\\\\', "'": "\\'", '\n': '\\n', '\t': '\\t'})
            return f"'{string.translate(escaping)}'"

        def format_expression(expression):
            if not expression:
                return ''
            elif expression[0] in ('byte', 'word', 'dword', 'value'):
                return ' '.join(map(str, expression))
            else:
                arguments = []
                for argument in expression[1]:
                    arguments.append(format_expression(argument))
                return f'{expression[0]}({", ".join(arguments)})'

        levels = []
        last_level = 0
        result = []

        for label, (code, *arguments) in sorted(blocks.items()):
            if label in special_labels:
                empty_prefix_line()
                append(f'{special_labels[label]}:', force_level=0)
                if len(levels) <= 1:
                    levels = [special_labels[label]]

            elif label in labels:
                empty_prefix_line()
                append(f'label_{label}:', force_level=0)

            if label in unreachable_labels and code not in (0xa2, 0xa3, 0xb8, 0xee):
                empty_prefix_line()
                append('// Unreachable code!')
                # TODO mark each line

            # FIXME sort
            if code == 'IF':
                empty_prefix_line()
                append(f'if {format_expression(arguments[0])}:')
                #result.extend(textwrap.wrap(f'if {format_expression(arguments[0])}:', subsequent_indent='    '))  # FIXME
                increase_level('if')

            elif code == 0xf8:
                empty_prefix_line()
                append(f'choice({format_string(arguments[0])})')

            elif code == 'PRINT':
                # FIXME smarter, with spaces at starts of lines, use minus all indent and print ?
                lines = textwrap.wrap(arguments[0], expand_tabs=False, replace_whitespace=False, drop_whitespace=False)
                assert ''.join(lines) == arguments[0]
                for line in lines:
                    append(f'print({format_string(line)})')

            elif code == 0xf7:
                empty_prefix_line()
                append('ask()')

            elif code == 0xb8:
                append('endOfList()')
                empty_prefix_line()

            elif code == 0xef:
                empty_prefix_line()
                decrease_level('case')
                for case in sorted(arguments[0]):
                    append(f'case {format_string(case)}:')
                increase_level('case')

            elif code == 0xa6:
                append(f'{format_expression(arguments[0])} = {format_expression(arguments[1])}')

            elif code == 0xee:
                remove_empty_line()
                decrease_level('esac')
                append('esac')
                append()

            elif code == 0x9c:
                append(f'horse({format_expression(arguments[0])})')

            elif code == 0xa2:
                remove_empty_line()
                decrease_level('if')
                append('fi')
                append()

            elif code == 0xf3:
                empty_prefix_line()
                append('f3()')

            elif code == 'WAIT':
                append('wait()')
                append()

            elif code == 0xa3:
                empty_prefix_line()
                decrease_level('if')
                append('else:')
                increase_level('if')

            elif code == 'BYE':
                append('bye()')
                append()

            elif code == 'SLEEP':
                append('sleep()')
                append()

            elif code == 0xff:
                append(f'id({arguments[0]})', force_level=0)

                if arguments[1] == 'Dr_ Cat':
                    name = arguments[1].replace('_', '.')
                elif arguments[1] == 'ed':
                    name = arguments[1].capitalize()
                else:
                    name = arguments[1]

                append(f'name({format_string(name)})', force_level=0)
                append()

            elif code in ('INTEGERS', 'STRINGS'):
                empty_prefix_line()
                if arguments[1][-1:] == ['unused']:
                    name = 'unused'
                    del arguments[1][-1]
                else:
                    name = 'integers' if code == 'INTEGERS' else 'strings'
                append(f'{name}_{label} = [', force_level=0)
                values = []
                for item in arguments[0]:
                    values.append(str(item) if code == 'INTEGERS' else format_string(item))
                max_size = max(map(len, values)) + 1
                for index, value in enumerate(values):
                    # FIXME переделать названия в выражениях
                    # FIXME pad numbers to right
                    # FIXME rjust indices of lists?
                    append(f'{value},'.ljust(max_size) + f' // {index}', force_level=1)
                append(f']', force_level=0)
                append()

            elif code == 'JUMP':
                if arguments[0] in special_labels:
                    append(f'jump {special_labels[arguments[0]]}')
                else:
                    append(f'jump label_{arguments[0]}')
                append()

            else:
                append(str((code, *arguments)))

        if result and result[-1] == '':
            del result[-1]

        return ''.join((line + '\n' for line in result))

    stream = io.BufferedReader(io.BytesIO(conversation))
    blocks = {}
    labels = set()
    visited_labels = set()
    data = {}
    special_labels = {}

    read_instructions(False)

    while labels - visited_labels:
        label = next(iter(labels - visited_labels))
        stream.seek(label)
        read_instructions(False)

    assert set(special_labels.values()) == {'description', 'interaction'}

    remaining_labels = set(range(len(conversation))) - visited_labels
    visited_data = set()
    unreachable_labels = set()
    error_labels = set()
    while set(data) != visited_data or remaining_labels != error_labels:
        types = dict(sorted(((label, data[label]) for label in set(data) - visited_data)))
        offsets = list(types)
        assert set(types.values()) <= {'integer', 'string'}

        for left, right in zip(offsets, offsets[1:] + [len(conversation)]):
            stream.seek(left)
            visited_data.add(left)
            if types[left] == 'integer':
                read_integers(False, right)

            else:
                assert types[left] == 'string'
                read_strings(right)

        remaining_labels -= visited_labels

        while remaining_labels - error_labels:
            label = min(remaining_labels - error_labels)
            stream.seek(label)
            # TODO ссылки могут не работать, чекнуть
            # TODO данные могут не работать, чекнуть
            read_instructions(True)
            remaining_labels -= visited_labels

    while remaining_labels:
        label = min(remaining_labels)
        stream.seek(label)
        read_integers(True, len(conversation))
        remaining_labels -= visited_labels

    return format_instructions()
