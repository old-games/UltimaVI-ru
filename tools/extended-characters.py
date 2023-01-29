import datetime
import os
import subprocess
import tempfile


functions = {
    'putch_impl': (0x464, 0x2efa),
    'toupper': (0x2ce6, 3),
}

def apply_obj(path, base):
    with open(path, 'rb') as f:
        data = f.read()
    index = 0
    fixups = {}
    externs = []
    fixmeups = set()
    code = b''
    while index < len(data):
        t = data[index]
        s = int.from_bytes(data[index+1:index+3], 'little')
        d = data[index+3:index+3+s]
        index += 3 + s

        if t == 0xa0:
            assert d[0] == 1
            assert len(code) == int.from_bytes(d[1:3], 'little')
            code += d[3:-1]

        elif t == 0x9c:
            d = d[:-1]
            i = 0
            z = None
            while i < len(d):
                if d[i] & 0x80:
                    assert d[i] & 4
                    assert d[i] & 0x78 == 0
                    z = d[i] & 3
                    i += 1
                else:
                    x = z << 8 | d[i]
                    u = d[i+1]
                    y = d[i+2]
                    i += 3
                    assert u, y == (0x56, 1)
                    fixups[x] = externs[0]
                    z = None
            assert d[0] == 0x85

        elif t == 0x8c:
            externs.append(d[1:1+d[0]].decode())

        elif t == 0x90:
            d = d[1:-2]
            i = 0
            while i < len(d):
                s = d[i+1]
                n = d[i+2:i+2+s].decode()
                a = int.from_bytes(d[i+2+s:i+4+s], 'little')
                if n.startswith('fixmeup'):
                    fixmeups.add(a)
                i += s + 4

    for a in fixmeups:
        assert code[a] == 0x9a
        more_relocs.append(base+a+3)

    assert not fixups
    return code


def replace(d, a, c):
    d[a:a+len(c)] = c


def nasm(code):
    with tempfile.TemporaryDirectory() as d:
        with open(f'{d}/1.asm', 'w') as f:
            f.write(f'bits 16\n{code}')
        r = subprocess.run(['nasm', f'{d}/1.asm', '-o', f'{d}/1'])
        r.check_returncode()
        with open(f'{d}/1', 'rb') as f:
            return f.read()


def pi_jump(s, a):
    s += space * 0x20
    # FIXME remove old relocs which could break these jumps.
    return b'\x8c\xc8\x2d' + s.to_bytes(2, 'little') + b'\x50\xb8' + a.to_bytes(2, 'little') + b'\x50\xcb'
    return nasm("""
; debugging
; n.b. this code is affected by old relocs
        xor ax, ax
        xor dx, dx

        mov cx, cs
        shr cx, 0x0c
        mov dl, cl
        and dx, 0x0f
        cmp dx, 9
        jle $+5
        add dl, 7
        add dl, 0x30
        mov ah, 2
        int 0x21

        mov cx, cs
        shr cx, 8
        mov dl, cl
        and dx, 0x0f
        cmp dx, 9
        jle $+5
        add dl, 7
        add dl, 0x30
        mov ah, 2
        int 0x21

        mov cx, cs
        shr cx, 4
        mov dl, cl
        and dx, 0x0f
        cmp dx, 9
        jle $+5
        add dl, 7
        add dl, 0x30
        mov ah, 2
        int 0x21

        mov cx, cs
        mov dl, cl
        and dl, 0x0f
        cmp dl, 9
        jle $+5
        add dl, 7
        add dl, 0x30
        mov ah, 2
        int 0x21

        jmp $+0
        """)


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('unpacked/GAME.EXE', 'rb') as f:
    d = bytearray(f.read())
    initial_size = len(d)

checksum = int.from_bytes(d[0x12:0x14], 'little')
assert sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) & 0xffff == 0xffff
pages = int.from_bytes(d[4:6], 'little')
cs = int.from_bytes(d[0x16:0x18], 'little')
ss = int.from_bytes(d[0x0e:0x10], 'little')
relocs = int.from_bytes(d[6:8], 'little')
header = int.from_bytes(d[8:0x0a], 'little') * 0x10
relocs_base = int.from_bytes(d[0x18:0x1a], 'little')

more_relocs = []

code_block = bytearray()
function_address = {}

r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True)
sha = f', {r.stdout.rstrip()}'.encode() if r.returncode == 0 else b''
code_block += b'Code was patched by Vladimir Chebotarev, ' + datetime.datetime.today().strftime('%Y-%m-%d').encode() + sha + b'. '
code_block += b'Please report issues to vladimir.chebotarev@gmail.com if any occur.'

with tempfile.TemporaryDirectory() as temp:
    for f in functions:
        subprocess.run(['nasm', '-f', 'obj', f'tools/{f}.asm', '-o', f'{temp}/{f}.obj']).check_returncode()
        function_address[f] = len(code_block)
        code_block += apply_obj(f'{temp}/{f}.obj', function_address[f])

code_block += b'\x00' * (0x200 - len(code_block) % 0x200)

assert set(d[relocs_base+4*relocs:header]) == {0}
assert len(d[relocs_base+4*relocs:header]) // 4 >= len(more_relocs)

print(f'Adding {len(code_block)} bytes')
space = len(code_block) // 0x200

for i, x in enumerate(more_relocs, start=relocs):
    old_segment = int.from_bytes(code_block[x:x+2], 'little')
    old_segment += space*0x20
    assert old_segment + 0x10 < 0x10000
    code_block[x:x+2] = old_segment.to_bytes(2, 'little')
    o = x % 0x10000
    s = x // 0x10000 * 0x1000
    d[relocs_base+i*4:relocs_base+i*4+2] = o.to_bytes(2, 'little')
    d[relocs_base+i*4+2:relocs_base+i*4+4] = s.to_bytes(2, 'little')

for i in range(relocs):
    offset = int.from_bytes(d[relocs_base+i*4:relocs_base+i*4+2], 'little')
    segment = int.from_bytes(d[relocs_base+i*4+2:relocs_base+i*4+4], 'little')
    value = int.from_bytes(d[offset+segment*0x10+header:offset+segment*0x10+2+header], 'little')
    value += space*0x20
    assert value + 0x10 < 0x10000
    d[offset+segment*0x10+header:offset+segment*0x10+2+header] = value.to_bytes(2, 'little')
    segment += space*0x20
    assert segment < 0x10000
    d[relocs_base+i*4+2:relocs_base+i*4+4] = segment.to_bytes(2, 'little')

relocs += len(more_relocs)

pages += space
d[6:8] = relocs.to_bytes(2, 'little')
cs += space*0x20
assert cs + 0x10 < 0x10000
d[0x16:0x18] = cs.to_bytes(2, 'little')
ss += space*0x20
assert ss + 0x10 < 0x10000
d[0x0e:0x10] = ss.to_bytes(2, 'little')
d[4:6] = pages.to_bytes(2, 'little')

assert d[0xb203:0xb206] == b'\x0d\x80\x00'
replace(d, 0xb204, b'\x00\x01') # 0x464:0x33d3, putch

for f, (cs, ip) in functions.items():
    replace(d, header+cs*0x10+ip, pi_jump(cs, function_address[f]))

def replace_check_size(d, o, s, x):
    assert len(x) == s, f'{len(x)} != {s}'
    d[o:o+s] = x

replace_check_size(d, 0x310b4, 0x2e, 'ХУЙ С РУНАМИ <ABCabc>! Функция: %d, ё: %d, ф: '.encode('cp866'))

assert len(d) == initial_size
d = d[:header] + code_block + d[header:]

checksum = (checksum - sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) + 0xffff) & 0xffff
d[0x12:0x14] = checksum.to_bytes(2, 'little')
assert sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) & 0xffff == 0xffff

os.chdir(output_directory)
with open('GAME.EXE', 'wb') as f:
    f.write(d)

# TODO: check / fix tolower / toupper / isalpha etc?
# TODO: игра буферизует символы в отдельном массиве перед выводом для того чтобы правильно разбивать на строки и они становятся байтами. Это нужно переделать.

# TODO: место из под старого кода можно переиспользовать, а также его relocs
# TODO: добавлять место более гранулярно чем постранично
