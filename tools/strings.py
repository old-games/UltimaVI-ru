import json
import os


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ds = {
    'GAME.EXE': 0x2d85,
}

printf = {
    'GAME.EXE': 0x04643643,
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

    for i in range(len(d)):
        if d[i:i+5] == b'\x9a' + printf[name].to_bytes(4, 'little'):
            if d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x50 and d[i-8] == 0xb8:
                a = int.from_bytes(d[i-7:i-5], 'little')
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                if (name, a*0x10+a2+0x3600) not in tt:
                    s = read_null_terminated(d, a*0x10+a2+0x3600)
                    tt[(name, a*0x10+a2+0x3600)] = s, 'FIXME ' + s

            elif d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x1e:
                a = ds[name]
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                if (name, a*0x10+a2+0x3600) not in tt:
                    s = read_null_terminated(d, a*0x10+a2+0x3600)
                    tt[(name, a*0x10+a2+0x3600)] = s, 'FIXME ' + s

            else:
                print(hex(i), hex(d[i-1]), 'UNKNOWN')

# TODO %s

t = [{'source': s, 'offset': o, 'english': en, 'russian': ru} for (s, o), (en, ru) in sorted(tt.items())]
with open('tools/translation.json', 'w') as f:
    f.write(json.dumps(t, indent=4, ensure_ascii=False))
