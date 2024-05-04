import tools.archive


def encode(book, language):
    items = []

    for entry in book:
        try:
            items.append(''.join(entry[language]).encode('cp866') + b'\x00')
        except UnicodeEncodeError as e:
            e.add_note(''.join(entry[language]))
            raise

    return tools.archive.encode(items, bits=16)
