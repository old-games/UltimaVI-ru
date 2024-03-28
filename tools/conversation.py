import io
import textwrap


# FIXME remove all this inside functions

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


def decode(conversation, source, index):
    def is_text(byte):
        return byte in (9, 0x0a) or 0x20 <= byte < 0x80

    def read_string(end):
        result = bytearray()
        while (byte := _peek_byte(stream)) is not None and byte not in end:
            _read_byte(stream, visited_labels)
            assert is_text(byte)
            result.append(byte)
        return result.decode('ascii')

    def try_read_string(end):
        result = bytearray()
        start = stream.tell()
        while (byte := _peek_byte(stream)) is not None and byte not in end:
            _read_byte(stream, set())
            if not is_text(byte):
                stream.seek(start)
                return None
            result.append(byte)
        stream.seek(start)
        return result.decode('ascii')

    def read_integers(unused, end):
        integers = []
        comments = []

        start_offset = stream.tell()
        assert start_offset not in blocks

        for offset in range(start_offset, end, 2):
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

        blocks[start_offset] = int, stream.tell()-start_offset, integers, comments # FIXME add?

    def read_strings(end):
        strings = []
        comments = []
        string = bytearray()

        start_offset = stream.tell()
        assert start_offset not in blocks

        for offset in range(start_offset, end):
            if offset in visited_labels:
                break

            # FIXME reuse try_read_string? without overlap
            if (byte := _peek_byte(stream)) and not is_text(byte):
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

        blocks[start_offset] = str, stream.tell()-start_offset, strings, comments # FIXME add?

    def read_instructions(unreachable):
        all_instructions = {
            0x9c, 0x9e,
            0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6,
            0xb0, 0xb5, 0xb6, 0xb8, 0xb9, 0xba, 0xbe, 0xbf,
            0xc4, 0xc5, 0xc9, 0xcb, 0xcd,
            0xd6, 0xd8, 0xd9, 0xdb,
            0xee, 0xef,
            0xf1, 0xf2, 0xf3, 0xf7, 0xf8, 0xf9, 0xfb, 0xfc,
        }
        # TODO there are more instructions in the game

        def add(*args):
            instruction = code, stream.tell() - offset, *args
            assert offset not in blocks or blocks[offset] == instruction
            blocks[offset] = instruction

        def add_branch_ended(stack):
            if stack:
                parent = stack[:-1]
                if stack[-1][0] == 'else' and branches_ended[(*parent, ('if', stack[-1][1]))]:
                    add_branch_ended(parent)
                elif stack[-1][0] == 'case':
                    if '*' in keywords[tuple(stack)]:
                        add_branch_ended(parent)
                    elif choices.get(tuple(parent)) is not None: # Mondain, no ask, no tell.
                        choices[tuple(parent)] -= keywords[tuple(stack)]
                        if not choices[tuple(parent)]:
                            add_branch_ended(parent)
            branches_ended[tuple(stack)] = True

        def one(collection):
            assert len(collection) == 1
            return collection[0]

        def set_data_type(offset, type):
            assert data[offset] in (None, type)
            # FIXME Can also collect and check afterwards.
            data[offset] = type

        def read_variable():
            value = _read_byte(stream, visited_labels)
            operator = _read_byte(stream, visited_labels)
            assert operator in (0xb2, 0xb3)
            # FIXME dont parse names, do it later
            return ({0xb2: 'integer', 0xb3: 'string'}[operator], [('value', value)])

        def read_expressions(end):
            # FIXME dont parse names, do it later
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
            # FIXME Address by code
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

        # Выходим, если читать больше нечего или встретились с данными в unreachable коде или выполнение, с которого мы начали, закончилось.
        while (code := _peek_byte(stream)) is not None and ((offset := stream.tell()) not in data or not unreachable) and not branches_ended[tuple()]:
            # Проверим, что не встречаемся с данными в обычном коде.
            assert offset not in data

            if offset in visited_labels:
                # Необходимо прочитать код повторно, если мы прыгнули на новую метку, контекст может закончиться раньше или позже, чем в прошлый раз.
                if unreachable and offset not in unreachable_labels:
                    unreachable = False

            # FIXME compress (simplify)
            if code == 0x9c:
                _read_byte(stream, visited_labels)
                add(one(read_expressions(0xa7)))

            elif code == 0x9e:
                _read_byte(stream, visited_labels)
                add()

            elif code == 0xa1:
                _read_byte(stream, visited_labels)
                stack.append(('if', stream.tell()))
                branches_ended[tuple(stack)] = False
                add(one(read_expressions(0xa7)))

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
                add_branch_ended(stack)
                add(label)

            elif code == 0xb6:
                _read_byte(stream, visited_labels)
                add_branch_ended(stack)
                add()

            elif code in (0xa4, 0xa5):
                _read_byte(stream, visited_labels)
                left = one(read_expressions(0xa7))
                right = one(read_expressions(0xa7))
                add(left, right)

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

                add(left, right)

            elif code == 0xb5:
                _read_byte(stream, visited_labels)
                index, strings = read_expressions(0xa7)
                assert strings[0] == 'dword'
                data.setdefault(strings[1], None)
                set_data_type(strings[1], 'string')
                add(strings, index)

            elif code == 0xb8:
                _read_byte(stream, visited_labels)
                add()

            elif code in (0xb9, 0xba):
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(4)]
                add(*arguments)

            elif code in (0xbe, 0xbf, 0xc4, 0xc5):
                _read_byte(stream, visited_labels)
                add(one(read_expressions(0xa7)))

            elif code == 0xc9:
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(4)]

                if arguments[1][0] == 'data': # TODO probably typehint other instructions too.
                    set_data_type(arguments[1][1][0][1], 'integer')

                add(*arguments)

            elif code == 0xcb:
                _read_byte(stream, visited_labels)
                add()

            elif code == 0xcd:
                _read_byte(stream, visited_labels)
                arguments = [one(read_expressions(0xa7)) for _ in range(2)]
                add(*arguments)

            elif code in (0xd6, 0xd8, 0xd9, 0xdb):
                _read_byte(stream, visited_labels)
                add(one(read_expressions(0xa7)))

            elif code == 0xee:
                # May be absent.
                _read_byte(stream, visited_labels)
                if stack and stack[-1][0] == 'case':
                    del stack[-1]
                add()

            elif code == 0xef:
                # TODO can't have nested keywords
                _read_byte(stream, visited_labels)
                argument = read_string({0xf6}).split(',')
                _read_byte(stream, visited_labels)
                # TODO вложенные ask в case ? leak choices to parent
                if stack and stack[-1][0] == 'case':
                    del stack[-1]
                stack.append(('case', stream.tell()))
                keywords[tuple(stack)] = set(argument)
                branches_ended[tuple(stack)] = False
                add(argument)
                if _peek_byte(stream) == 0xef:
                    blocks[offset+1] = ..., ... # Derydlus

            elif code == 0xf2:
                _read_byte(stream, visited_labels)
                # FIXME multiple interactions
                special_labels[stream.tell()] = 'interaction'
                add()

            elif code == 0xf1:
                _read_byte(stream, visited_labels)
                # FIXME multiple descriptions
                special_labels[stream.tell()] = 'description'
                add()

            elif code == 0xf3:
                _read_byte(stream, visited_labels)
                add()

            elif code == 0xf7:
                _read_byte(stream, visited_labels)
                choices[tuple(stack)] = None
                add()

            elif code == 0xf8:
                _read_byte(stream, visited_labels)
                argument = read_string(all_instructions)
                choices[tuple(stack)] = set(argument)
                add(argument)

            elif code in (0xf9, 0xfb, 0xfc):
                _read_byte(stream, visited_labels)
                add(read_variable())

            elif code == 0xff:
                _read_byte(stream, visited_labels)
                add(_read_byte(stream, visited_labels), read_string({0xf1, 0xf3}))

            elif try_read_string(all_instructions):
                code = None
                add(read_string(all_instructions))

            else:
                assert unreachable
                error_labels.add(offset)
                break

            if unreachable:
                unreachable_labels.add(offset)

    def format_instructions():
        all_instructions = {
            0x9c: 'createHorse', 0x9e: 'sleep',
            0xa4: 'setBit', 0xa5: 'clearBit',
            0xb5: 'printString', 0xb6: 'bye',
            0xb8: 'endOfList', 0xb9: 'createItem', 0xba: 'destroyItem', 0xbe: 'inventory', 0xbf: 'portrait',
            0xc4: 'increaseKarma', 0xc5: 'decreaseKarma', 0xc9: 'moveItem', 0xcb: 'wait', 0xcd: 'do',
            0xd6: 'resurrect', 0xd8: 'look', 0xd9: 'heal', 0xdb: 'cure',
            0xf3: 'f3', 0xf7: 'ask',
            0xf9: 'inputString', 0xfb: 'inputInteger', 0xfc: 'inputDigit',
        }
        empty_prefix = {
            # TODO
        }
        empty_suffix = {
            # TODO
        }

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

        def command():
            append(f'{all_instructions[code]}({", ".join((format_expression(argument) for argument in arguments))})')

        def empty_prefix_line():
            if result and result[-1] != '' and last_level >= len(levels):
                append()

        def remove_empty_line():
            if result and result[-1] == '':
                del result[-1]

        def format_string(string, case=False):
            escaping = str.maketrans({'\\': '\\\\', "'": "\\'", '\n': '\\n', '\t': '\\t'})
            escaped = string.translate(escaping)
            if not case:
                return '\n'.join((
                    '{',
                    f"{' '*(len(levels)+1)*4}'english': '{escaped}',",
                    f"{' '*(len(levels)+1)*4}'russian': 'FIXME {escaped}'",
                    f"{' '*len(levels)*4}{'}'}"
                ))
            elif string == '*':
                return "'*'"
            else:
                return '\n'.join((
                    f"'{escaped}':",
                    f"{' '*len(levels)*4}case {'{'}'russian': 'FIXME {escaped}'{'}'}"
                ))

        def format_expression(expression):
            if not expression:
                return ''
            elif expression[0] == 'dword' and expression[1] in data_labels:
                return data_labels[expression[1]]
            elif expression[0] in ('byte', 'word', 'dword', 'value'):
                return ' '.join(map(str, expression))
            else:
                arguments = []
                for argument in expression[1]:
                    arguments.append(format_expression(argument))
                return f'{expression[0]}({", ".join(arguments)})'

        data_labels = {}
        for label, (code, _, *arguments) in blocks:
            if code in (int, str):
                if arguments[1][-1:] == ['unused']:
                    name = 'unused'
                else:
                    name = 'integers' if code == int else 'strings'
                data_labels[label] = f'{name}_{label}'

        levels = []
        last_level = 0

        result = []

        for label, (code, _, *arguments) in blocks:
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

            # FIXME sort and compress
            if code == 0xa1:
                empty_prefix_line()
                append(f'if {format_expression(arguments[0])}:')
                #result.extend(textwrap.wrap(f'if {format_expression(arguments[0])}:', subsequent_indent='    '))  # FIXME
                increase_level('if')

            elif code == 0xf8:
                empty_prefix_line()
                append(f'choice({format_string(arguments[0])})')

            elif code is None:
                # FIXME smarter, with spaces at starts of lines, use minus all indent and print ?
                lines = textwrap.wrap(arguments[0], expand_tabs=False, replace_whitespace=False, drop_whitespace=False)
                assert ''.join(lines) == arguments[0]
                for line in lines:
                    append(f'print({format_string(line)})')

            elif code is ...:
                append('nop()')

            elif code == 0xef:
                empty_prefix_line()
                decrease_level('case')
                for case in arguments[0]:
                    append(f'case {format_string(case, case=True)}:')
                increase_level('case')

            elif code == 0xa6:
                append(f'{format_expression(arguments[0])} = {format_expression(arguments[1])}')

            elif code == 0xee:
                remove_empty_line()
                decrease_level('esac')
                append('esac')
                append()

            elif code in (0x9c, 0xa4, 0xa5, 0xb5, 0xb9, 0xba, 0xbe, 0xbf, 0xc4, 0xc5, 0xc9, 0xcd, 0xd6, 0xd8, 0xd9, 0xdb, 0xf9, 0xfb, 0xfc):
                command()

            elif code in (0xf1, 0xf2):
                pass

            elif code == 0xa2:
                remove_empty_line()
                decrease_level('if')
                append('fi')
                append()

            elif code in (0xf3, 0xf7):
                empty_prefix_line()
                command()

            elif code == 0xa3:
                empty_prefix_line()
                decrease_level('if')
                append('else:')
                increase_level('if')

            elif code in (0x9e, 0xb6, 0xb8, 0xcb):
                command()
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

            elif code in (int, str):
                empty_prefix_line()
                name = data_labels[label]
                if arguments[1][-1:] == ['unused']:
                    del arguments[1][-1]
                append(f'{name} = [', force_level=0)
                values = []
                for item in arguments[0]:
                    values.append(str(item) if code == int else format_string(item))
                max_size = max((len(value.splitlines()[-1]) for value in values)) + 1
                for index, value in enumerate(values):
                    # FIXME переделать названия в выражениях
                    # FIXME pad numbers to right
                    # FIXME rjust indices of lists?
                    append(f'{value},'.ljust(max_size) + f' // {index}', force_level=1)
                append(f']', force_level=0)
                append()

            elif code == 0xb0:
                if arguments[0] in special_labels:
                    append(f'jump {special_labels[arguments[0]]}')
                else:
                    append(f'jump label_{arguments[0]}')
                append()

            else:
                assert False

        if result and result[-1] == '':
            del result[-1]

        return ''.join((line + '\n' for line in result))

    stream = io.BufferedReader(io.BytesIO(conversation))
    blocks = {}
    labels = set()
    visited_labels = set()
    jumped_labels = set()
    data = {}
    special_labels = {}

    read_instructions(False)

    while labels - jumped_labels:
        label = next(iter(labels - jumped_labels))
        jumped_labels.add(label)
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

    # Unglue.
    blocks = sorted(blocks.items())
    for i in range(len(blocks)):
        if blocks[i][1][0] is not ...:
            for j in range(i+1, len(blocks)):
                if blocks[j][1][0] is not ...:
                    left_end = blocks[i][0] + blocks[i][1][1]
                    right = blocks[j][0]
                    assert left_end == right or left_end > right and blocks[i][1][0] is None and blocks[j][1][0] is None
                    if left_end > right:
                        assert left_end == right + blocks[j][1][1]
                        cut = left_end - right
                        blocks[i] = blocks[i][0], (blocks[i][1][0], blocks[i][1][1]-cut, blocks[i][1][2][:-cut])
                    break

    return f"source('{source}')\nindex({index})\n\n{format_instructions()}"


def encode(conversation, target_language, version):
    assert version in (1, 2) and target_language in ('english', 'russian') and (version == 2 or target_language == 'english')

    # FIXME remove copy-paste
    operators = {
        'greater': 0x81, 'greaterOrEquals': 0x82, 'less': 0x83, 'lessOrEquals': 0x84, 'notEquals': 0x85, 'equals': 0x86,
        'plus': 0x90, 'minus': 0x91, 'multiply': 0x92, 'divide': 0x93, 'or': 0x94, 'and': 0x95,
        'canCarry': 0x9a, 'weight': 0x9b, 'hasHorse': 0x9d, 'hasObject': 0x9f,
        'random': 0xa0, 'hasBit': 0xab,
        'integer': 0xb2, 'string': 0xb3, 'data': 0xb4, 'indexOf': 0xb7, 'objectsCount': 0xbb,
        'partyHas': 0xc6, 'partyHasObject': 0xc7, 'partyJoin': 0xca, 'partyLeave': 0xcc,
        'isNearby': 0xd7, 'isWounded': 0xda, 'isPoisoned': 0xdc, 'character': 0xdd,
        'experience': 0xe0, 'level': 0xe1, 'strength': 0xe2, 'intelligence': 0xe3, 'dexterity': 0xe4,
    }
    # FIXME remove copy-paste
    parameters = {operator: 1 for operator in (
        'canCarry', 'hasHorse', 'integer', 'string', 'partyHas', 'partyJoin', 'partyLeave',
        'isNearby', 'isWounded', 'isPoisoned'
    )}
    parameters.update({operator: 2 for operator in operators if operator not in parameters})
    parameters.update({operator: 3 for operator in ('hasObject',)})

    def tokens():
        def token():
            if chars:
                yield ''.join(chars)
                chars.clear()

        chars = []
        is_string = False
        is_comment = False
        while char := stream.read(1):
            if char == '/' and not is_comment and not is_string:
                char = stream.read(1)
                assert char == '/'
                is_comment = True

            elif char == '\n' and is_comment:
                is_comment = False

            elif is_comment:
                pass

            elif char in ' \t\n' and not is_string:
                yield from token()

            elif char == "'":
                if is_string:
                    chars.append(char)
                yield from token()
                is_string = not is_string
                if is_string:
                    chars.append(char)

            elif char == '\\' and is_string:
                char = stream.read(1)
                assert len(char) == 1
                char = {'n': '\n', 't': '\t'}.get(char, char)
                chars.append(char)

            elif char in ',:{}()' and not is_string:
                yield from token()
                yield char

            else:
                chars.append(char)

        assert not chars or not is_string
        token()

    def selected():
        for token in (iterator := tokens()):
            if token == '{':
                languages = {}
                while token != '}':
                    language = unquote(next(iterator))
                    assert language not in languages
                    assert language in ('english', 'russian')
                    assert next(iterator) == ':'
                    token = next(iterator)
                    unquote(token)
                    languages[language] = token
                    token = next(iterator)
                    assert token in ',}'
                yield languages.get(target_language)

            else:
                yield token

    def joined_cases():
        def join_cases():
            if cases:
                yield 'case'
                yield ','.join((unquote(case) for case in cases))
                cases.clear()
                yield ':'

        cases = []
        for token in (iterator := selected()):
            if token == 'case':
                case = next(iterator)
                if case is not None: # TODO Support no cases scenario.
                    cases.append(case)
                assert next(iterator) == ':'

            else:
                yield from join_cases()
                yield token

        yield from join_cases()

    def read_expression(token=None):
        # FIXME value переименовать в small???
        # FIXME inventory в showInventory
        # FIXME portrait в showPortrait
        # FIXME look == showCharacter???? do?

        operator = next(iterator) if token is None else token

        if operator in ('value', 'byte', 'word', 'dword'): # FIXME copy-paste
            value = int(next(iterator))
            if operator == 'value':
                assert 0 <= value < 0x80
                result.append(value)
            elif operator == 'byte':
                result.append(0xd3)
                result.append(value)
            elif operator == 'word':
                result.append(0xd4)
                result.extend(value.to_bytes(2, 'little'))
            elif operator == 'dword':
                result.append(0xd2)
                result.extend(value.to_bytes(4, 'little'))
            return

        assert operator in operators
        assert next(iterator) == '('

        if operator in ('data', 'indexOf'): # FIXME copy-paste?
            array = next(iterator)
            result.append(0xd2)
            placeholders[len(result)] = array
            dangerous_placeholders.add(len(result))
            result.extend(b'\x00\x00\x00\x00')
            assert next(iterator) == ','
            read_expression()

        else:
            for index in range(parameters[operator]):
                if index:
                    assert next(iterator) == ','
                read_expression()

        result.append(operators[operator])
        assert next(iterator) == ')'

    def is_string(token):
        return isinstance(token, str) and len(token) >= 2 and token[0] == token[-1] == "'"

    def unquote(token):
        assert is_string(token)
        return token[1:-1]

    def write_string(string, context):
        if context == 'strings':
            start = b''
            end = b'\x00'
        elif version == 2 and context == 'print':
            start = b'\x04'
            end = b'\x00'
        else:
            start = b''
            end = b''
        result.extend(start + string.encode('ascii' if version == 1 else 'cp866') + end)

    def add_label():
        assert token not in labels
        labels[token] = len(result)

    result = bytearray()
    stream = io.StringIO(conversation)
    iterator = joined_cases()

    assert next(iterator) == 'source'
    assert next(iterator) == '('
    source = unquote(next(iterator))
    assert next(iterator) == ')'

    assert next(iterator) == 'index'
    assert next(iterator) == '('
    index = int(next(iterator))
    assert next(iterator) == ')'

    labels = {}
    placeholders = {}
    dangerous_placeholders = set()

    for token in iterator:
        if token == 'id':
            assert next(iterator) == '('
            result.append(0xff)
            result.append(int(next(iterator)))
            assert next(iterator) == ')'

        elif token == 'name':
            assert next(iterator) == '('
            name = unquote(next(iterator))
            write_string(name, 'name')
            assert next(iterator) == ')'

        elif token == 'description':
            assert next(iterator) == ':'
            result.append(0xf1 if version == 1 else 1)
            add_label()

        elif token == 'print':
            assert next(iterator) == '('
            write_string(unquote(next(iterator)), 'print')
            assert next(iterator) == ')'

        elif token == 'f3':
            assert next(iterator) == '('
            result.append(0xf3)
            assert next(iterator) == ')'

        elif token == 'sleep':
            assert next(iterator) == '('
            result.append(0x9e)
            assert next(iterator) == ')'

        elif token == 'endOfList':
            assert next(iterator) == '('
            result.append(0xb8)
            assert next(iterator) == ')'

        elif token == 'bye':
            assert next(iterator) == '('
            result.append(0xb6)
            assert next(iterator) == ')'

        elif token == 'inputString':
            assert next(iterator) == '('
            result.append(0xf9)
            read_expression()
            assert next(iterator) == ')'

        elif token == 'inputInteger':
            assert next(iterator) == '('
            result.append(0xfb)
            read_expression()
            assert next(iterator) == ')'

        elif token == 'inputDigit':
            assert next(iterator) == '('
            result.append(0xfc)
            read_expression()
            assert next(iterator) == ')'

        elif token == 'do':
            assert next(iterator) == '('
            result.append(0xcd)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'look':
            assert next(iterator) == '('
            result.append(0xd8)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'resurrect':
            assert next(iterator) == '('
            result.append(0xd6)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'inventory':
            assert next(iterator) == '('
            result.append(0xbe)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'createItem':
            assert next(iterator) == '('
            result.append(0xb9)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'destroyItem':
            assert next(iterator) == '('
            result.append(0xba)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'moveItem':
            assert next(iterator) == '('
            result.append(0xc9)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'wait':
            assert next(iterator) == '('
            result.append(0xcb)
            assert next(iterator) == ')'

        elif token == 'interaction':
            assert next(iterator) == ':'
            result.append(0xf2)
            add_label()

        elif token == 'ask':
            assert next(iterator) == '('
            result.append(0xf7)
            assert next(iterator) == ')'

        elif token == 'if':
            result.append(0xa1)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ':'

        elif token == 'else':
            result.append(0xa3 if version == 1 else 3)
            assert next(iterator) == ':'

        elif token == 'fi':
            result.append(0xa2 if version == 1 else 2)

        elif token == 'jump':
            result.append(0xb0)
            label = next(iterator)
            placeholders[len(result)] = label
            result.extend(b'\x00\x00\x00\x00')

        elif token == 'case':
            result.append(0xef if version == 1 else 0x0f)
            case = next(iterator)
            write_string(case, 'case')
            result.append(0xf6)
            assert next(iterator) == ':'

        elif token == 'esac':
            result.append(0xee if version == 1 else 0x0e)

        elif token == 'createHorse':
            assert next(iterator) == '('
            result.append(0x9c)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'setBit':
            assert next(iterator) == '('
            result.append(0xa4)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'clearBit':
            assert next(iterator) == '('
            result.append(0xa5)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'portrait':
            assert next(iterator) == '('
            result.append(0xbf)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'heal':
            assert next(iterator) == '('
            result.append(0xd9)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'printString':
            assert next(iterator) == '('
            result.append(0xb5)
            array = next(iterator)
            result.append(0xd2)
            placeholders[len(result)] = array
            dangerous_placeholders.add(len(result))
            result.extend(b'\x00\x00\x00\x00')
            assert next(iterator) == ','
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'increaseKarma':
            assert next(iterator) == '('
            result.append(0xc4)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'decreaseKarma':
            assert next(iterator) == '('
            result.append(0xc5)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'cure':
            assert next(iterator) == '('
            result.append(0xdb)
            read_expression()
            result.append(0xa7)
            assert next(iterator) == ')'

        elif token == 'choice':
            assert next(iterator) == '('
            result.append(0xf8)
            write_string(unquote(next(iterator)), 'choice')
            assert next(iterator) == ')'

        elif token in operators:
            result.append(0xa6)
            read_expression(token)
            assert next(iterator) == '='
            result.append(0xa8)
            read_expression()
            result.append(0xa7)

        elif token == 'nop':
            assert next(iterator) == '('
            assert next(iterator) == ')'

        elif (next_token := next(iterator)) == ':':
            add_label()

        elif next_token == '=':
            add_label()
            assert (token := next(iterator)) == '['
            array = token
            value_type = None
            while token != ']':
                value = next(iterator)
                if value == ']':
                    break # Trailing comma.
                if value_type is None:
                    value_type = is_string(value)
                else:
                    assert value_type == is_string(value)
                if is_string(value):
                    write_string(unquote(value), 'strings')
                else:
                    result.extend(int(value).to_bytes(2, 'little'))
                token = next(iterator)
                assert token in ',]'

        else:
            assert False

    for offset, label in placeholders.items():
        data = labels[label].to_bytes(4, 'little')
        result[offset:offset+4] = data
        dangerous_ff = 0xb0 in data or 0xd4 in data[2:4] or 0xd3 == data[3]
        assert offset not in dangerous_placeholders or not dangerous_ff, 'Flow may be broken'

    return source, index, result
