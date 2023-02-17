import json
import os
import re
import subprocess


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


printf = {
    'END.EXE': [0x063a022b, 0x063a024b, 0x063a0279],
    'GAME.EXE': [0x04643643],
    'U.EXE': [0x12ee0229, 0x12ee0249, 0x12ee0277],
}


FIXME = """
END.EXE Not found: seven
END.EXE Not found: twenty-one
END.EXE Not found: twenty-two
END.EXE Not found: twenty-six
END.EXE Not found: twenty-nine
GAME.EXE Not found: savegame\objblkaa
GAME.EXE Not found: midi.dat
GAME.EXE Not found: portrait.a
U.EXE Not found: mainmenu.cga
U.EXE Not found: NSCA
U.EXE Not found: SPTA
"""


def read_null_terminated(d, i):
    s = ''
    assert d[i] != 0
    while d[i]:
        assert d[i] in b'\r\n\b\t' + bytes(range(0x20, 0x80))
        s += d[i:i+1].decode('ascii')
        i += 1
    return s


def add_string(name, offset, s):
    if (name, offset) not in tt:
        tt[(name, offset)] = (s, f'FIXME {s}')


def add_reference(name, offset, origin, type, segment):
    rr.setdefault((name, offset), [])
    origins = [(x['origin'], x['segment']) for x in rr[(name, offset)]]
    if (origin, segment) not in origins:
        rr[(name, offset)].append({'origin': origin, 'segment': segment, 'type': type})


with open('tools/translation.json') as f:
    t = json.loads(f.read())

tt = {(x['source'], x['offset']): (x['english'], x['russian']) for x in t}

with open('tools/references.json') as f:
    r = json.loads(f.read())

rr = {(x['source'], x['offset']): x['references'] for x in r}

for name, printfs in printf.items():
    with open(f'unpacked/{name}', 'rb') as f:
        d = f.read()

    base = int.from_bytes(d[8:0x0a], 'little')*0x10
    relocs_base = int.from_bytes(d[0x18:0x1a], 'little')
    relocs = int.from_bytes(d[6:8], 'little')

    segments = set()
    for i in range(relocs):
        offset = int.from_bytes(d[relocs_base+i*4:relocs_base+i*4+2], 'little')
        segment = int.from_bytes(d[relocs_base+i*4+2:relocs_base+i*4+4], 'little')
        value = int.from_bytes(d[offset+segment*0x10+base:offset+segment*0x10+2+base], 'little')
        segments.add(value)

    ds = max(segments)

    # FIXME объединять одинаковые строки в одну.

    calls = [b'\x9a' + func.to_bytes(4, 'little') for func in printfs]
    for i in range(base, ds*0x10+base): # FIXME этот цикл на самом деле не нужен.
        if d[i] == 0x9a:
            is_printf = d[i:i+5] in calls
            if d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x50 and d[i-8] == 0xb8:
                a = int.from_bytes(d[i-7:i-5], 'little')
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                try:
                    o = a*0x10 + a2 + base
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i-3, 'register', i-7)
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

            elif d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x1e:
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                try:
                    o = ds*0x10 + a2 + base
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i-3, 'register', 'ds') # FIXME ds может быть unknown
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

    for i in range(ds*0x10+base, len(d), 1):
        a2 = int.from_bytes(d[i:i+2], 'little')
        try:
            o = ds*0x10 + a2 + base
            assert d[o-1] == 0 # FIXME
            s = read_null_terminated(d, o)
            add_string(name, o, s)
            add_reference(name, o, i, 'data', 'ds') # FIXME ds может быть unknown
        except (IndexError, UnicodeDecodeError, AssertionError):
            pass

    for segment in segments:
        for i in range(ds*0x10+base, len(d), 1):
            a2 = int.from_bytes(d[i:i+2], 'little')
            try:
                o = segment*0x10 + a2 + base
                assert d[o-1] == 0 # FIXME
                s = read_null_terminated(d, o)
                add_string(name, o, s)
                add_reference(name, o, i, 'data', 'unknown')
            except (IndexError, UnicodeDecodeError, AssertionError):
                pass

    for segment_offset in (-2, +2):
        for i in range(ds*0x10+base, len(d), 2):
            a = int.from_bytes(d[i+segment_offset:i+segment_offset+2], 'little')
            a2 = int.from_bytes(d[i:i+2], 'little')
            try:
                assert a != 0
                o = a*0x10 + a2 + base
                assert d[o-1] == 0 # FIXME
                s = read_null_terminated(d, o)
                add_string(name, o, s)
                add_reference(name, o, i, 'data', i+segment_offset)
            except (IndexError, UnicodeDecodeError, AssertionError):
                pass

    for i in range(base, ds*0x10+base):
        if d[i] in range(0xb8, 0xc0): # segments around?
            a2 = int.from_bytes(d[i+1:i+3], 'little')
            try:
                o = ds*0x10 + a2 + base
                assert d[o-1] == 0 # FIXME
                s = read_null_terminated(d, o)
                add_string(name, o, s)
                add_reference(name, o, i+1, 'register', 'ds') # FIXME ds может быть unknown
            except (IndexError, UnicodeDecodeError, AssertionError):
                pass

    for segment in segments:
        for i in range(base, ds*0x10+base):
            if d[i] in range(0xb8, 0xc0): # segments around?
                a2 = int.from_bytes(d[i+1:i+3], 'little')
                try:
                    o = segment*0x10 + a2 + base
                    assert d[o-1] == 0 # FIXME
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i+1, 'register', 'unknown')
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

            if d[i:i+2] == b'\x66\x68':
                a2 = int.from_bytes(d[i+2:i+4], 'little')
                try:
                    o = segment*0x10 + a2 + base
                    assert d[o-1] == 0 # FIXME
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i+1, 'argument', 'unknown')
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

# TODO %s

t = [{'source': s, 'offset': o, 'english': en, 'russian': ru} for (s, o), (en, ru) in sorted(tt.items())]
with open('tools/translation.json', 'w') as f:
    print(json.dumps(t, indent=4, ensure_ascii=False), file=f)

r = [{'source': s, 'offset': o, 'text': tt[(s, o)][0], 'references': sorted(d, key=lambda x: (x['origin'], x['segment'] if isinstance(x['segment'], int) else 0))} for (s, o), d in sorted(rr.items())]
with open('tools/references.json', 'w') as f:
    f.write(json.dumps(r, indent=4, ensure_ascii=False))

c = 0
for name in printf:
    r = subprocess.run(['strings', f'unpacked/{name}'], stdout=subprocess.PIPE, universal_newlines=True)
    r.check_returncode()
    t = {x for (s, _), (e, _) in tt.items() if s == name for x in re.split('[\n\r\b\t]+', e) if x}
    for i in r.stdout.splitlines():
        if i not in t:
            print(name, 'Not found:', i)
            c += 1

print(len(tt), len(rr), c)
