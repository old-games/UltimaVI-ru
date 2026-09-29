import json
import os
import re
import subprocess

import tools


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

printf = {
    'END.EXE': [0x063a022b, 0x063a024b, 0x063a0279],
    'GAME.EXE': [0x04643643],
    'INSTALL.EXE': [], # FIXME
    'U.EXE': [0x12ee0229, 0x12ee0249, 0x12ee0277],
}


def read_null_terminated(d, i):
    s = ''
    assert d[i] != 0
    while d[i]:
        assert d[i] in b'\r\n\b\t' + bytes(range(0x20, 0x80))
        s += d[i:i+1].decode('ascii')
        i += 1
    return s


def add_string(name, offset, s):
    if (name, offset) not in ns:
        if (name, offset) not in tt:
            tt[(name, offset)] = (s, f'FIXME {s}')


def add_reference(name, offset, origin, type, segment):
    if (name, offset) not in ns:
        rr.setdefault((name, offset), [])
        origins = [(x['origin'], x['segment']) for x in rr[(name, offset)]]
        if (origin, segment) not in origins:
            rr[(name, offset)].append({'origin': origin, 'segment': segment, 'type': type})


tt = {}
rr = {}

with open('patches/not-strings.json', 'r') as f:
    ns = {(d['source'], d['offset']) for d in json.loads(f.read())}

for name, printfs in printf.items():
    with open(tools.get_path(name), 'rb') as f:
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

    segments = sorted(segments)
    dss = segments[-3:] if name == 'GAME.EXE' else segments[-1:]
    sss = segments[-2:] if name == 'GAME.EXE' else segments[-1:]

    # FIXME объединять одинаковые строки в одну.

    # Ссылки на printf-строки из каждого сегмента кода из кода.
    calls = [b'\x9a' + func.to_bytes(4, 'little') for func in printfs]
    for ds, next_ds in zip(sss, sss[1:] + [None]):
        for i in range(base, dss[0]*0x10+base+15):
            if d[i:i+5] in calls:
                if d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x50 and d[i-8] == 0xb8:
                    a = int.from_bytes(d[i-7:i-5], 'little')
                    if a == ds:
                        a2 = int.from_bytes(d[i-3:i-1], 'little')
                        try:
                            assert not next_ds or a2 < (next_ds-ds)*0x10+15
                            o = a*0x10 + a2 + base
                            s = read_null_terminated(d, o)
                            add_string(name, o, s)
                            add_reference(name, o, i-3, 'register', i-7)
                        except (IndexError, UnicodeDecodeError, AssertionError):
                            pass

                elif d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x1e:
                    a2 = int.from_bytes(d[i-3:i-1], 'little')
                    try:
                        assert not next_ds or a2 < (next_ds-ds)*0x10+15
                        o = ds*0x10 + a2 + base
                        s = read_null_terminated(d, o)
                        add_string(name, o, s)
                        add_reference(name, o, i-3, 'register', 'unknown')
                    except (IndexError, UnicodeDecodeError, AssertionError):
                        pass

                else:
                    pass

            # TODO %s

    # Ссылки из DS из данных.
    for ds, next_ds in zip(sss, sss[1:] + [None]):
        for i in range(dss[0]*0x10+base, len(d), 1):
            a2 = int.from_bytes(d[i:i+2], 'little')
            try:
                assert not next_ds or a2 < (next_ds-ds)*0x10+15
                o = ds*0x10 + a2 + base
                assert d[o-1] == 0
                s = read_null_terminated(d, o)
                add_string(name, o, s)
                add_reference(name, o, i, 'data', 'unknown')
            except (IndexError, UnicodeDecodeError, AssertionError):
                pass

    # Far ссылки из DS из данных.
    for segment_offset in (-2, +2):
        for i in range(dss[0]*0x10+base, len(d), 1):
            a = int.from_bytes(d[i+segment_offset:i+segment_offset+2], 'little')
            for ds, next_ds in zip(sss, sss[1:] + [None]):
                if a == ds:
                    a2 = int.from_bytes(d[i:i+2], 'little')
                    try:
                        assert not next_ds or a2 < (next_ds-ds)*0x10+15
                        o = a*0x10 + a2 + base
                        assert d[o-1] == 0
                        s = read_null_terminated(d, o)
                        add_string(name, o, s)
                        add_reference(name, o, i, 'data', i+segment_offset)
                    except (IndexError, UnicodeDecodeError, AssertionError):
                        pass

    # Ссылки из каждого сегмента кроме DS из кода.
    for ds, next_ds in zip(sss, sss[1:] + [None]):
        for i in range(base, dss[0]*0x10+base+15):
            # TODO manual indexing with [bx+...]
            if d[i-1] in (5, 0x68, *range(0xb8, 0xc0)) or d[i-2:i] in (b'\x8a\x87',) or d[i-4:i-2] in (b'\xc7\x06',) or d[i-3:i-1] in (b'\xc7\x46',):
                a2 = int.from_bytes(d[i:i+2], 'little')
                try:
                    assert not next_ds or a2 < (next_ds-ds)*0x10+15
                    o = ds*0x10 + a2 + base
                    assert d[o-1] == 0
                    s = read_null_terminated(d, o)
                    add_string(name, o, s)
                    add_reference(name, o, i, 'argument' if d[i-1] == 0x68 or d[i-4:i-2] == b'\xc7\x06' else 'register', 'unknown')
                except (IndexError, UnicodeDecodeError, AssertionError):
                    pass

if os.path.isfile('patches/translation.json'):
    with open('patches/translation.json') as f:
        t = json.loads(f.read())
    old_tt = {(x['source'], x['offset']): (x['english'], x['russian']) for x in t}
else:
    old_tt = {}

if 'merge':
    for t in set(old_tt) & set(tt):
        if not old_tt[t][1].startswith('FIXME '):
            tt[t] = old_tt[t]
    for t in set(old_tt) - set(tt):
        if t in {
            ('GAME.EXE', 201222),
            ('END.EXE', 34725),
            ('END.EXE', 34738),
            ('END.EXE', 34751),
            ('END.EXE', 34764),
            ('END.EXE', 34777),
            ('END.EXE', 34790),
            ('END.EXE', 34816),
            ('END.EXE', 34829),
            ('END.EXE', 34842),
            ('END.EXE', 34855),
            ('END.EXE', 34868),
            ('END.EXE', 34881),
            ('END.EXE', 34894),
            ('END.EXE', 34907),
            ('END.EXE', 34920),
            ('END.EXE', 34933),
            ('END.EXE', 34959),
            ('END.EXE', 34972),
            ('END.EXE', 35011),
            ('END.EXE', 35024),
            ('END.EXE', 35037),
            ('END.EXE', 35089),
            ('U.EXE', 92069),
            ('U.EXE', 92078),
            ('U.EXE', 92087),
            ('U.EXE', 92096),
            ('U.EXE', 92105),
            ('U.EXE', 92114),
            ('U.EXE', 92123),
        }:
            tt[t] = old_tt[t] # FIXME numbers and classes


t = [{'source': s, 'offset': o, 'english': en, 'russian': ru} for (s, o), (en, ru) in sorted(tt.items()) if (s, o) not in ns]
with open('patches/translation.json', 'w') as f:
    print(json.dumps(t, indent=4, ensure_ascii=False), file=f)

r = [{'source': s, 'offset': o, 'text': tt[(s, o)][0], 'references': sorted(d, key=lambda x: (x['origin'], x['segment'] if isinstance(x['segment'], int) else 0))} for (s, o), d in sorted(rr.items())]
with open('patches/references.json', 'w') as f:
    f.write(json.dumps(r, indent=4, ensure_ascii=False))

c = 0
for name in printf:
    r = subprocess.run(['strings', tools.get_path(name)], stdout=subprocess.PIPE, universal_newlines=True, check=True)
    t = {x for (s, _), (e, _) in tt.items() if s == name for x in re.split('[\n\r\b\t]+', e) if x}
    for i in r.stdout.splitlines():
        if i not in t:
            print(name, 'Not found:', i)
            c += 1

print(len(tt), len(rr), c)

if 'check':
    for t in sorted(set(old_tt) - set(tt)):
        if not old_tt[t][1].startswith('FIXME '):
            print('Removed', t, old_tt[t])
