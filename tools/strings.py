import json
import os
import subprocess


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


dsegs = {
    'END.EXE': 0x07b4,
    'GAME.EXE': 0x2d85,
    'U.EXE': 0x1499,
}

printf = {
    'END.EXE': [0x063a022b, 0x063a024b, 0x063a0279],
    'GAME.EXE': [0x04643643],
    'U.EXE': [0x12ee0229, 0x12ee0249, 0x12ee0277],
}


def read_null_terminated(d, i):
    s = ''
    assert d[i] != 0
    while d[i]:
        assert d[i] in b'\r\n\b' + bytes(range(0x20, 0x80))
        s += d[i:i+1].decode('ascii')
        i += 1
    return s


def add_string(name, offset, s):
    if (name, offset) not in tt:
        tt[(name, offset)] = (s, f'FIXME {s}')


def add_reference(name, offset, origin, type):
    rr.setdefault((name, offset), [])
    origins = [x['origin'] for x in rr[(name, offset)]]
    if not origin in origins:
        rr[(name, offset)].append({'origin': origin, 'type': type})


with open('tools/translation.json') as f:
    t = json.loads(f.read())

tt = {(x['source'], x['offset']): (x['english'], x['russian']) for x in t}

with open('tools/references.json') as f:
    r = json.loads(f.read())

rr = {(x['source'], x['offset']): x['references'] for x in r}

for name, ds in dsegs.items():
    with open(f'unpacked/{name}', 'rb') as f:
        d = f.read()

    base = int.from_bytes(d[8:0x0a], 'little')*0x10

    calls = [b'\x9a' + func.to_bytes(4, 'little') for func in printf[name]]
    for i in range(base, ds*0x10+base):
        if d[i] == 0x9a:
            is_printf = d[i:i+5] in calls
            if d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x50 and d[i-8] == 0xb8:
                a = int.from_bytes(d[i-7:i-5], 'little')
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                try:
                    o = a*0x10 + a2 + base
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i-4, 'register')
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

            elif d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x1e:
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                try:
                    o = ds*0x10 + a2 + base
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i-4, 'register')
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

            elif printf:
                print(name, hex(i), hex(d[i-1]), 'UNKNOWN')

    for i in range(ds*0x10+base, len(d), 2):
        a2 = int.from_bytes(d[i:i+2], 'little')
        try:
            assert d[ds*0x10+a2+base-1] == 0
            o = ds*0x10 + a2 + base
            s = read_null_terminated(d, o)
            add_string(name, o, s)
            add_reference(name, o, i, 'data')
        except (IndexError, UnicodeDecodeError, AssertionError):
            pass

    for i in range(base, ds*0x10+base):
        if d[i] in range(0xb8, 0xc0):
            a2 = int.from_bytes(d[i+1:i+3], 'little')
            try:
                o = ds*0x10 + a2 + base
                assert d[o-1] == 0
                s = read_null_terminated(d, o)
                add_string(name, o, s)
                add_reference(name, o, i, 'register')
            except (IndexError, UnicodeDecodeError, AssertionError):
                pass

# TODO %s

t = [{'source': s, 'offset': o, 'english': en, 'russian': ru} for (s, o), (en, ru) in sorted(tt.items())]
with open('tools/translation.json', 'w') as f:
    f.write(json.dumps(t, indent=4, ensure_ascii=False))

r = [{'source': s, 'offset': o, 'text': tt[(s, o)][0], 'references': d} for (s, o), d in sorted(rr.items())]
with open('tools/references.json', 'w') as f:
    f.write(json.dumps(r, indent=4, ensure_ascii=False))

c = 0
for name in dsegs:
    r = subprocess.run(['strings', f'unpacked/{name}'], stdout=subprocess.PIPE, universal_newlines=True)
    r.check_returncode()
    t = {e.replace('\n', '').replace('\r', '').replace('\b', '') for (s, _), (e, _) in tt.items() if s == name}
    for i in r.stdout.splitlines():
        if i not in t:
            print(name, 'Not found:', i)
            c += 1

print(len(tt), len(rr), c)
