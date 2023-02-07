import json
import os
import subprocess


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ds = {
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
    while d[i]:
        s += d[i:i+1].decode()
        i += 1
    return s


with open('tools/translation.json') as f:
    t = json.loads(f.read())

tt = {(x['source'], x['offset']): (x['english'], x['russian']) for x in t}

for name in ds:
    with open(f'unpacked/{name}', 'rb') as f:
        d = f.read()

    base = int.from_bytes(d[8:0x0a], 'little')*0x10

    calls = [b'\x9a' + func.to_bytes(4, 'little') for func in printf[name]]
    for i in range(len(d)):
        if d[i:i+5] in calls:
            print(name, hex(i))
            if d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x50 and d[i-8] == 0xb8:
                a = int.from_bytes(d[i-7:i-5], 'little')
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                if (name, a*0x10+a2+base) not in tt:
                    s = read_null_terminated(d, a*0x10+a2+base)
                    tt[(name, a*0x10+a2+base)] = s, 'FIXME ' + s

            elif d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x1e:
                a = ds[name]
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                if (name, a*0x10+a2+base) not in tt:
                    s = read_null_terminated(d, a*0x10+a2+base)
                    tt[(name, a*0x10+a2+base)] = s, 'FIXME ' + s

            else:
                print(name, hex(i), hex(d[i-1]), 'UNKNOWN')

# TODO %s

t = [{'source': s, 'offset': o, 'english': en, 'russian': ru} for (s, o), (en, ru) in sorted(tt.items())]
with open('tools/translation.json', 'w') as f:
    f.write(json.dumps(t, indent=4, ensure_ascii=False))

c = 0
for name in ds:
    r = subprocess.run(['strings', f'unpacked/{name}'], stdout=subprocess.PIPE, universal_newlines=True)
    r.check_returncode()
    t = {e for (s, _), (e, _) in tt.items() if s == name}
    for i in r.stdout.splitlines():
        if i not in t:
            print(name, 'Not found:', i)
            c += 1

print(len(tt), c)
