"""Чтение и запись таблиц XLSX/CSV «Системы Переводчик» без сторонних библиотек.

Таблица — список строк, строка — список ячеек-строк (A оригинал, B перевод, C ключ, D пояснение). Читается активный
лист, как в СП; числа и прочие значения возвращаются строками. Управляющие символы в XLSX хранятся как `_xHHHH_`.
"""

import csv
import io
import posixpath
import re
import zipfile
from xml.etree import ElementTree
from xml.sax.saxutils import escape

MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RELATIONSHIPS = '{http://schemas.openxmlformats.org/package/2006/relationships}'
DOCUMENT_RELATIONSHIPS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
ESCAPED = re.compile(r'_x([0-9A-Fa-f]{4})_')
# Символы, которые нельзя записать в XML, и само начало записи `_xHHHH_`.
UNSAFE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]|_(?=x[0-9A-Fa-f]{4}_)')


def _unescape(text):
    return ESCAPED.sub(lambda match: chr(int(match[1], 16)), text)


def _escape(text):
    return escape(UNSAFE.sub(lambda match: f'_x{ord(match[0]):04X}_', text))


def _text(element):
    """Текст ячейки или общей строки: <t> или набор <r><t>."""
    if element is None:
        return ''
    parts = [t.text or '' for t in element.iter(f'{MAIN}t')]
    return _unescape(''.join(parts))


def _column(reference):
    number = 0
    for char in re.match(r'[A-Z]+', reference)[0]:
        number = number * 26 + ord(char) - ord('A') + 1
    return number - 1


def read_xlsx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        workbook = ElementTree.fromstring(archive.read('xl/workbook.xml'))
        relationships = ElementTree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {item.get('Id'): item.get('Target') for item in relationships.iter(f'{RELATIONSHIPS}Relationship')}
        sheets = list(workbook.iter(f'{MAIN}sheet'))
        view = workbook.find(f'{MAIN}bookViews/{MAIN}workbookView')
        active = int(view.get('activeTab', 0)) if view is not None else 0
        target = targets[sheets[active].get(f'{DOCUMENT_RELATIONSHIPS}id')]
        path = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
        shared = []
        if 'xl/sharedStrings.xml' in names:
            strings = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
            shared = [_text(item) for item in strings.iter(f'{MAIN}si')]
        sheet = ElementTree.fromstring(archive.read(path))
    rows = []
    for row in sheet.iter(f'{MAIN}row'):
        number = int(row.get('r', len(rows) + 1))
        while len(rows) < number - 1:
            rows.append([])
        cells = []
        for cell in row.iter(f'{MAIN}c'):
            column = _column(cell.get('r')) if cell.get('r') else len(cells)
            kind = cell.get('t', 'n')
            if kind == 'inlineStr':
                value = _text(cell.find(f'{MAIN}is'))
            else:
                raw = cell.find(f'{MAIN}v')
                raw = '' if raw is None or raw.text is None else raw.text
                value = shared[int(raw)] if kind == 's' else _unescape(raw) if kind == 'str' else raw
            while len(cells) < column:
                cells.append('')
            cells.append(value)
        rows.append(cells)
    return rows


def write_xlsx(rows):
    """Один лист, все ячейки — строки (inlineStr), без заголовка."""
    lines = []
    for number, row in enumerate(rows, 1):
        cells = ''.join(
            f'<c r="{chr(ord("A") + column)}{number}" t="inlineStr"><is><t xml:space="preserve">{_escape(value)}</t></is></c>'
            for column, value in enumerate(row)
        )
        lines.append(f'<row r="{number}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(lines)}</sheetData></worksheet>'
    )
    files = {
        '[Content_Types].xml': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        '_rels/.rels': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>'
        ),
        'xl/workbook.xml': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Worksheet" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        'xl/_rels/workbook.xml.rels': (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        'xl/worksheets/sheet1.xml': sheet,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content.encode('utf-8'))
    return output.getvalue()


def read_csv(data):
    text = data.decode('utf-8-sig')
    delimiter = ','
    if text.startswith('sep='):
        line, _, text = text.partition('\n')
        delimiter = line[4:].strip() or ','
    return [row for row in csv.reader(io.StringIO(text, newline=''), delimiter=delimiter)]


def write_csv(rows):
    output = io.StringIO(newline='')
    csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator='\n').writerows(rows)
    return output.getvalue().encode('utf-8')


def read(name, data):
    return read_csv(data) if name.lower().endswith('.csv') else read_xlsx(data)


def write(name, rows):
    return write_csv(rows) if name.lower().endswith('.csv') else write_xlsx(rows)
