import collections
import json
import os

import tools


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_null_terminated(d, i):
    s = ''
    while d[i]:
        s += d[i:i+1].decode()
        i += 1
    return s


with open('tools/translation.json') as f:
    t = json.loads(f.read())

by_source = collections.defaultdict(list)

for i in t:
    assert set(i.keys()) == {'source', 'offset', 'english', 'russian'}
    assert i['source'] in {'GAME.EXE', 'END.EXE', 'INSTALL.EXE', 'U.EXE', 'ULTIMA6.EXE'}, f'Invalid source: "{i["source"]}".'
    assert isinstance(i['offset'], int)
    by_source[i['source']].append(i)

for s, ii in by_source.items():
    with open(tools.get_binary_path(s), 'rb') as f:
        x = f.read()
    for i in ii:
        text = read_null_terminated(x, i['offset'])
        assert text == i['english'], f'English text could not be found at offset {i["offset"]}: "{i["english"]}".'

with open('tools/not-strings.json') as f:
    ns = json.loads(f.read())

by_source = collections.defaultdict(list)

for i in ns:
    assert set(i.keys()) == {'source', 'offset', 'text'}
    assert i['source'] in {'GAME.EXE', 'END.EXE', 'INSTALL.EXE', 'U.EXE', 'ULTIMA6.EXE'}, f'Invalid source: "{i["source"]}".'
    assert isinstance(i['offset'], int)
    by_source[i['source']].append(i)

for s, ii in by_source.items():
    with open(tools.get_binary_path(s), 'rb') as f:
        x = f.read()
    for i in ii:
        text = read_null_terminated(x, i['offset'])
        assert text == i['text'], f'Text could not be found at offset {i["offset"]}: "{i["text"]}".'

with open('tools/references.json') as f:
    r = json.loads(f.read())
# FIXME

with open('tools/bad-references.json') as f:
    br = json.loads(f.read())
# FIXME
