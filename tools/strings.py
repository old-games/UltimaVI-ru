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


for name in ds:
    with open(f'unpacked/{name}', 'rb') as f:
        d = f.read()

    for i in range(len(d)):
        if d[i:i+5] == b'\x9a' + printf[name].to_bytes(4, 'little'):
            if d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x50 and d[i-8] == 0xb8:
                a = int.from_bytes(d[i-7:i-5], 'little')
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                print(hex(i), repr(read_null_terminated(d, a*0x10+a2+0x3600)))

            elif d[i-1] == 0x50 and d[i-4] == 0xb8 and d[i-5] == 0x1e:
                a = ds[name]
                a2 = int.from_bytes(d[i-3:i-1], 'little')
                print(hex(i), repr(read_null_terminated(d, a*0x10+a2+0x3600)))

            else:
                print(hex(i), hex(d[i-1]), 'UNKNOWN')

# TODO %s
