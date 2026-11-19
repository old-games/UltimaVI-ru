"""Диалоги и графика из «Системы Переводчик» (translate.old-games.ru, проект Ultima VI).

В СП диалоги — один текстовый перевод: на каждую реплику `{'english': …, 'russian': …}` из conversations/*.txt
фраза «оригинал | перевод» в том виде, как в файле сценария (`\\n`, `\\'`, `\\\\`). Перед репликами файла — строка-
заголовок с именем файла и пустым переводом. Ключевые слова (`case {'russian': …}`), сценарии, тексты EXE, осмотра
и книг в СП не переводятся — они правятся в git.

python3 -m tools.sp import <выгрузка СП: project.zip или каталог> [--dry-run] [--report отчёт.md]
    Вписывает переводы реплик в conversations/*.txt (меняется только текст в 'russian': '…') и перерисовки в
    graphics/ (tools.shapes). Реплики сопоставляются по ключам (колонка C), а в выгрузке без ключей — по
    заголовкам и порядку. Английский текст сверяется с файлом: не совпал — файл (без ключей) или реплика (с
    ключами) не меняется. Не меняется и реплика, которую нельзя записать или собрать (символ не из CP866, байт-
    команда игры, `\\` в конце). Код выхода: 0 — всё применено, 2 — есть неприменённые фразы, 1 — сбой.

python3 -m tools.sp keys <выгрузка СП> <out.xlsx|out.csv>
    Таблица для «Обновить из файла» (по порядку): те же A и B, что в выгрузке, плюс ключи (C) и пояснения (D).
"""

import hashlib
import json
import os
import re
import sys

import tools
import tools.conversation
import tools.file
import tools.shapes
import tools.xlsx

SITE = 'https://translate.old-games.ru'
PAGE_SIZE = 300  # фраз на странице перевода в СП
CONVERSATIONS = 'conversations'
GRAPHICS = 'graphics'

ENGLISH = re.compile(r"^\s*'english'\s*:\s*'((?:\\.|[^'\\])*)'\s*,\s*$")
RUSSIAN = re.compile(r"^(\s*'russian'\s*:\s*')((?:\\.|[^'\\])*)('\s*)$")
SUBSTITUTION = re.compile(r'[$#][0-9A-Z]')
KEY_PREFIX = 'CONV'


class Pair:
    """Реплика в файле сценария: строки 'english' и 'russian' (номера с 0) и сырой текст как в файле."""

    def __init__(self, line, english, russian, prefix, suffix, context):
        self.line = line
        self.english = english
        self.russian = russian
        self.prefix = prefix
        self.suffix = suffix
        self.context = context
        self.key = None


class Conversation:
    def __init__(self, name, text):
        self.name = name
        self.lines = text.split('\n')
        self.pairs = []
        self.source = re.search(r"^source\('([^']*)'\)", text, re.M)
        self.id = re.search(r'^id\((\d+)\)', text, re.M)
        for i, line in enumerate(self.lines):
            if "'english'" not in line:
                continue
            english = ENGLISH.match(line)
            russian = RUSSIAN.match(self.lines[i + 1]) if english and i + 1 < len(self.lines) else None
            assert english and russian, f'{name}.txt:{i + 1}: expected a line with \'english\' and then \'russian\'.'
            context = self.lines[i - 1].strip() if i else ''
            self.pairs.append(Pair(i + 1, english[1], russian[2], russian[1], russian[3], context))
        seen = {}
        for pair in self.pairs:
            digest = hashlib.sha1(pair.english.encode('utf-8')).hexdigest()[:6]
            seen[digest] = seen.get(digest, 0) + 1
            pair.key = f'{KEY_PREFIX}:{key_name(name)}:{digest}' + (f'.{seen[digest]}' if seen[digest] > 1 else '')

    def text(self):
        return '\n'.join(self.lines)


def key_name(name):
    return re.sub(r'[^A-Za-z0-9._-]', '_', name)


def load_conversations(path):
    conversations = {}
    for file_name in sorted(os.listdir(path), key=str.lower):
        if file_name.endswith('.txt'):
            name = file_name[:-4]
            conversations[name] = Conversation(name, tools.file.read(os.path.join(path, file_name)).decode('utf-8'))
    names = {}
    for name in conversations:
        assert key_name(name) not in names, f'{name} and {names[key_name(name)]} give the same key.'
        names[key_name(name)] = name
    return conversations


def decode(raw):
    """Сырой текст из файла сценария → строка, как её читает tools.conversation."""
    result = []
    i = 0
    while i < len(raw):
        if raw[i] == '\\' and i + 1 < len(raw):
            result.append({'n': '\n', 't': '\t'}.get(raw[i + 1], raw[i + 1]))
            i += 2
        else:
            result.append(raw[i])
            i += 1
    return ''.join(result)


def check_translation(value, english):
    """Перевод из СП → (сырой текст для файла или None, ошибки, предупреждения)."""
    errors = []
    warnings = []
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    raw = []
    i = 0
    while i < len(value):
        char = value[i]
        if char == '\\':
            if i + 1 == len(value):
                errors.append('`\\` в конце строки: для обратной косой черты пишите `\\\\`')
                break
            following = value[i + 1]
            if following in '\n\t':
                errors.append('`\\` перед настоящим переводом строки или табуляцией')
                break
            if following not in "nt\\'":
                warnings.append(f'`\\{following}` читается как `{following}` (обратная косая пропадает)')
            raw.append(char + following)
            i += 2
            continue
        raw.append({"'": "\\'", '\n': '\\n', '\t': '\\t'}.get(char, char))
        i += 1
    raw = ''.join(raw)
    text = decode(raw).translate(tools.conversation.INVISIBLE)
    foreign = []
    for char in text:
        try:
            char.encode('cp866')
        except UnicodeEncodeError:
            if char not in foreign:
                foreign.append(char)
    if foreign:
        errors.append('символы не из CP866 (в игре их нет): ' + ', '.join(f'«{c}» U+{ord(c):04X}' for c in foreign))
    if not errors:
        opcodes = sorted({b for b in text.encode('cp866') if b in tools.conversation.TEXT_OPCODES})
        if opcodes:
            errors.append('байты-команды игры ' + ', '.join(f'{b:#04x}' for b in opcodes))
    if value.strip():
        wanted = sorted(SUBSTITUTION.findall(decode(english)))
        found = sorted(SUBSTITUTION.findall(text))
        if wanted != found:
            warnings.append(f'подстановки {" ".join(found) or "нет"}, в оригинале {" ".join(wanted) or "нет"}')
    return (None if errors else raw), errors, warnings


class Export:
    """Текстовый перевод диалогов из выгрузки СП."""

    def __init__(self, files):
        self.files = files
        self.manifest = json.loads(files['manifest.json']) if 'manifest.json' in files else None
        if self.manifest:
            texts = [item for item in self.manifest['translations'] if item['type'] == 'text']
            assert len(texts) == 1, 'Expected one text translation (dialogues) in the export, found: ' + ', '.join(
                f"{item['id']} «{item['title']}»" for item in texts
            )
            self.translation = texts[0]
            path = self.translation['path']
        else:
            tables = [path for path in files if '/' not in path and path.lower().endswith(('.xlsx', '.csv'))]
            assert len(tables) == 1, f'Expected one table in the export, found: {tables}'
            self.translation = None
            path = tables[0]
        self.path = path
        self.rows = [(row + [''] * 4)[:4] for row in tools.xlsx.read(path, files[path])]
        self.keyed = any(row[2].strip() for row in self.rows)

    def link(self, row_number, key=None):
        if not self.translation:
            return f'строка {row_number} выгрузки'
        base = f"{SITE}/translations/{self.translation['id']}"
        if key:
            return f'[{key}]({base}?key={key})'
        return f'[строка {row_number}]({base}?page={(row_number - 1) // PAGE_SIZE + 1}#phrase{row_number})'

    def groups(self, names):
        """Без ключей: {имя файла: [(номер строки, английский, перевод)]} по строкам-заголовкам и
        {имя файла: номер строки заголовка}."""
        groups = {}
        headers = {}
        current = None
        for number, (english, russian, _, _) in enumerate(self.rows, 1):
            header = english.strip() in names and not russian.strip()
            # Первая реплика файла — имя персонажа (английский = имя файла); с пустым переводом она похожа на
            # заголовок, но идёт сразу за заголовком того же файла.
            if header and not (current == english.strip() and not groups[current]):
                current = english.strip()
                assert current not in groups, f'Header {current} occurs twice (row {number}).'
                groups[current] = []
                headers[current] = number
                continue
            assert current is not None, f'Row {number} comes before the first file header.'
            groups[current].append((number, english, russian))
        return groups, headers


class Result:
    def __init__(self):
        self.changes = {}  # имя файла → число изменённых реплик
        self.errors = []
        self.warnings = []
        self.graphics = []

    def report(self, export):
        lines = ['# Ultima VI: перевод из СП', '']
        if export.manifest:
            translation = export.translation
            lines.append(
                f"Выгрузка {export.manifest.get('revision', '')}, перевод «{translation['title']}» "
                f"({translation['translated']} из {translation['phrases']} фраз), "
                f"{'по ключам' if export.keyed else 'без ключей, по порядку'}."
            )
            lines.append('')
        total = sum(self.changes.values())
        lines.append(f'Диалоги: изменено реплик — {total}, файлов — {len(self.changes)}.')
        if self.changes:
            lines.append('')
            lines.append(', '.join(f'{name} ({count})' for name, count in sorted(self.changes.items())))
        lines.append('')
        lines.append(f'Графика: изменений — {len(self.graphics)}.')
        for change in self.graphics:
            lines.append(f'- {change}')
        for title, items in (
            ('Не применено (в git остался прежний текст)', self.errors),
            ('Предупреждения (применено)', self.warnings),
        ):
            if items:
                lines += ['', f'## {title}: {len(items)}', '']
                lines += [f'- {item}' for item in items]
        return '\n'.join(lines) + '\n'


def where(export, name, pair, row_number, key=None):
    return f'{name}.txt:{pair.line + 1} ({export.link(row_number, key)})'


def apply(conversations, export, result):
    """Переводы из выгрузки → conversations (в памяти)."""
    names = set(conversations)
    if export.keyed:
        rows = {}
        for number, (english, russian, key, _) in enumerate(export.rows, 1):
            key = key.strip()
            if not key:
                result.warnings.append(f'{export.link(number)}: фраза без ключа — пропущена')
                continue
            if key.count(':') == 1:  # заголовок файла
                continue
            rows[key] = (number, english, russian)
        used = set()
        for name, conversation in conversations.items():
            for pair in conversation.pairs:
                if pair.key not in rows:
                    result.warnings.append(
                        f'{name}.txt:{pair.line + 1}: реплики нет в СП, добавьте фразу с ключом `{pair.key}`'
                    )
                    continue
                used.add(pair.key)
                number, english, russian = rows[pair.key]
                if english != pair.english:
                    result.errors.append(
                        f'{where(export, name, pair, number, pair.key)}: английский не совпадает с файлом'
                    )
                    continue
                update(export, conversation, pair, number, russian, result, pair.key)
        for key in sorted(set(rows) - used):
            result.warnings.append(f'{export.link(rows[key][0], key)}: в сценариях такой реплики нет')
        return
    groups, _ = export.groups(names)
    for name in sorted(set(groups) - names):
        result.errors.append(f'{name}: в СП есть, файла conversations/{name}.txt нет')
    for name, conversation in conversations.items():
        if name not in groups:
            result.errors.append(f'{name}.txt: в СП нет заголовка файла — файл не изменён')
            continue
        rows = groups[name]
        if len(rows) != len(conversation.pairs):
            result.errors.append(
                f'{name}.txt: реплик в файле {len(conversation.pairs)}, в СП {len(rows)} — файл не изменён'
            )
            continue
        mismatch = next(((pair, row) for pair, row in zip(conversation.pairs, rows) if pair.english != row[1]), None)
        if mismatch:
            pair, (number, _, _) = mismatch
            result.errors.append(
                f'{where(export, name, pair, number)}: английский не совпадает с файлом — файл не изменён'
            )
            continue
        for pair, (number, _, russian) in zip(conversation.pairs, rows):
            update(export, conversation, pair, number, russian, result)


def update(export, conversation, pair, number, value, result, key=None):
    name = conversation.name
    raw, errors, warnings = check_translation(value, pair.english)
    if raw == pair.russian:
        return
    place = where(export, name, pair, number, key)
    if errors:
        result.errors += [f'{place}: {error}' for error in errors]
        return
    result.warnings += [f'{place}: {warning}' for warning in warnings]
    if pair.russian.strip() and not raw.strip():
        result.warnings.append(f'{place}: перевод стёрт (было `{pair.russian}`)')
    conversation.lines[pair.line] = pair.prefix + raw + pair.suffix
    pair.russian = raw
    result.changes[name] = result.changes.get(name, 0) + 1


def import_export(source, dry_run=False, report_path=None, root=None):
    root = root or tools.get_script_path()
    files = tools.shapes.read_export(source)
    export = Export(files)
    conversations_path = os.path.join(root, CONVERSATIONS)
    conversations = load_conversations(conversations_path)
    result = Result()
    apply(conversations, export, result)
    if tools.shapes.has_frames(files):
        result.graphics = tools.shapes.import_files(
            files, os.path.join(root, GRAPHICS), os.path.join(root, 'original'), write=not dry_run
        )
    if not dry_run:
        for name in result.changes:
            path = os.path.join(conversations_path, f'{name}.txt')
            tools.file.write(path, conversations[name].text().encode('utf-8'))
    report = result.report(export)
    print(report)
    if report_path:
        tools.file.write(report_path, report.encode('utf-8'))
    return result


def keys(source, output, root=None):
    """Выгрузка без ключей → та же таблица с ключами и пояснениями."""
    export = Export(tools.shapes.read_export(source))
    assert not export.keyed, 'The export already has keys.'
    conversations = load_conversations(os.path.join(root or tools.get_script_path(), CONVERSATIONS))
    groups, headers = export.groups(set(conversations))
    assert set(groups) == set(conversations), (
        f'Files differ: only in SP {sorted(set(groups) - set(conversations))}, '
        f'only in git {sorted(set(conversations) - set(groups))}'
    )
    notes = {}
    for name, conversation in conversations.items():
        rows = groups[name]
        assert len(rows) == len(
            conversation.pairs
        ), f'{name}: {len(rows)} phrases in SP, {len(conversation.pairs)} in git.'
        source = conversation.source[1] if conversation.source else '?'
        number = conversation.id[1] if conversation.id else '?'
        for pair, (row, english, _) in zip(conversation.pairs, rows):
            assert english == pair.english, f'{name}.txt:{pair.line}: English differs from row {row}.'
            note = f'{name} ({source}, №{number})'
            if pair.context.startswith('name('):
                note += '. Имя персонажа'
            hints = [
                hint
                for code, hint in (
                    ('\\n', '\\n — новая строка'),
                    ("\\'", "\\' — апостроф"),
                    ('\\\\', '\\\\ — обратная косая черта'),
                )
                if code in pair.english
            ]
            if hints:
                note += '. Текст как в файле сценария: ' + ', '.join(hints)
            notes[row] = (pair.key, note)
    header_keys = {
        row: (f'{KEY_PREFIX}:{key_name(name)}', f'Служебная строка: начало диалога {name}. Не переводить.')
        for name, row in headers.items()
    }
    table = []
    for number, (english, russian, _, _) in enumerate(export.rows, 1):
        key, note = notes.get(number) or header_keys.get(number) or (None, None)
        assert key, f'Row {number}: neither a phrase nor a file header.'
        table.append([english, russian, key, note])
    tools.file.write(output, tools.xlsx.write(output, table))
    print(f'{len(table)} rows → {output}')


def main():
    args = sys.argv[1:]
    assert args and args[0] in ('import', 'keys'), __doc__
    if args[0] == 'keys':
        assert len(args) == 3, __doc__
        keys(args[1], args[2])
        return
    dry_run = '--dry-run' in args
    args = [arg for arg in args if arg != '--dry-run']
    report_path = None
    if '--report' in args:
        i = args.index('--report')
        report_path = args[i + 1]
        del args[i : i + 2]
    assert len(args) == 2, __doc__
    result = import_export(args[1], dry_run, report_path)
    sys.exit(2 if result.errors else 0)


if __name__ == '__main__':
    main()
