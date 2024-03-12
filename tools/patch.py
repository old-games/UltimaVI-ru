import binascii
import datetime
import json
import os
import subprocess
import tempfile

import tools


add_functions = {
    'END.EXE': {
    },
    'GAME.EXE': {
        'putch_impl': (0x464, 0x2efa, 0x3e4),
        'toupper': (0x2ce6, 3, 0x31),
    },
    'U.EXE': {
    },
}

# TODO: место из под старого кода можно переиспользовать
# TODO: добавлять место более гранулярно чем постранично


def ljust(d, n, p):
    r = d + p*((n - len(d) + len(p)-1)//len(p))
    r[n:] = []
    return r


def find_all(d, pattern):
    results = []
    for i in range(len(d)):
        for j, x in enumerate(pattern):
            if x is not None:
                if x != d[i+j]:
                    break
        else:
            results.append(i)
    return results


def apply_obj(path, base):
    with open(path, 'rb') as f:
        data = f.read()
    index = 0
    externs = []
    fixmeups = set()
    code = bytearray()
    while index < len(data):
        t = data[index]
        s = int.from_bytes(data[index+1:index+3], 'little')
        d = data[index+3:index+3+s]
        index += 3 + s

        if t == 0xa0:
            assert d[0] == 1
            assert len(code) == int.from_bytes(d[1:3], 'little')
            last_code = len(code)
            code += d[3:-1]

        elif t == 0x9c:
            d = d[:-1]
            i = 0
            while i < len(d):
                assert d[i] & 0xfc == 0xc4
                x = d[i+1] | (d[i] & 3) << 8
                u = d[i+1]
                y = d[i+2]
                assert u, y == (0x54, 1) # local data
                code[last_code+x:last_code+x+2] = (base+int.from_bytes(code[last_code+x:last_code+x+2], 'little')).to_bytes(2, 'little')
                # TODO call near
                # TODO call far
                i += 4

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
        relocs.append((base+a+3, 0, False, False))

    return code


def replace(d, a, c):
    d[a:a+len(c)] = c


def nasm(code):
    with tempfile.TemporaryDirectory() as d:
        with open(f'{d}/1.asm', 'w') as f:
            f.write(f'bits 16\n{code}')
        r = subprocess.run(['nasm', '-f', 'bin', f'{d}/1.asm', '-o', f'{d}/1.com'])
        r.check_returncode()
        with open(f'{d}/1.com', 'rb') as f:
            return f.read()


def jump(s, a, os, oa):
    relocs.append((oa+3, os, True, True))
    return b'\xea' + a.to_bytes(2, 'little') + s.to_bytes(2, 'little')
    relocs.append((oa+1, os, True, True))
    return b'\x68' + s.to_bytes(2, 'little') + b'\x68' + a.to_bytes(2, 'little') + b'\xcb'


def pi_jump(s, a):
    s += space * 0x20
    return b'\x8c\xc8\x2d' + s.to_bytes(2, 'little') + b'\x50\xb8' + a.to_bytes(2, 'little') + b'\x50\xcb'
    return nasm("""
        ; debugging

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

with open('tools/translation.json') as f:
    translation = json.loads(f.read())

with open('tools/references.json') as f:
    references = {(x['source'], x['offset']): x['references'] for x in json.loads(f.read())}

replaced = 0
added = 0
missing = 0

for binary, functions in add_functions.items():
    with open(f'unpacked/{binary}', 'rb') as f:
        d = bytearray(f.read())

    checksum = int.from_bytes(d[0x12:0x14], 'little')
    original_checksum = sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) & 0xffff
    assert original_checksum in (0xffff, 0x80df, 0x3dc1)
    pages = int.from_bytes(d[4:6], 'little')
    cs = int.from_bytes(d[0x16:0x18], 'little')
    ss = int.from_bytes(d[0x0e:0x10], 'little')
    relocs_size = int.from_bytes(d[6:8], 'little')
    header = int.from_bytes(d[8:0x0a], 'little') * 0x10
    relocs_base = int.from_bytes(d[0x18:0x1a], 'little')
    relocs = []
    segments = set()
    for i in range(relocs_size):
        offset = int.from_bytes(d[relocs_base+i*4:relocs_base+i*4+2], 'little')
        segment = int.from_bytes(d[relocs_base+i*4+2:relocs_base+i*4+4], 'little')
        segments.add(int.from_bytes(d[offset+segment*0x10+header:offset+segment*0x10+2+header], 'little'))
        relocs.append((offset, segment, False, True))
    segments = sorted(segments)

    code_block = bytearray()
    function_address = {}

    sha = tools.get_sha()
    sha = f', {sha}'.encode() if sha else b''

    code_block += b'Code was patched by Vladimir Chebotarev, ' + datetime.datetime.today().strftime('%Y-%m-%d').encode() + sha + b'. '
    code_block += b'Please report issues to vladimir.chebotarev@gmail.com if any occur.'

    with tempfile.TemporaryDirectory() as temp:
        for f in functions:
            subprocess.run(['nasm', '-f', 'obj', f'tools/{os.path.splitext(binary)[0]}/{f}.asm', '-o', f'{temp}/{f}.obj']).check_returncode()
            function_address[f] = len(code_block)
            code_block += apply_obj(f'{temp}/{f}.obj', function_address[f])

    code_block += b'\x00' * (0x200 - len(code_block) % 0x200)
    space = len(code_block) // 0x200

    if binary == 'GAME.EXE':
        assert d[0xb203:0xb206] == b'\x0d\x80\x00'
        replace(d, 0xb204, b'\x00\x01') # 0x0464:0x33d3, putch # FIXME выкинуть это в отдельный файл.

    uninitialized_fill, = find_all(d, [0xbf, None, None, 0xb9, None, None, 0x2b, 0xcf, 0xf3, 0xaa])
    initialized_size = int.from_bytes(d[uninitialized_fill+1:uninitialized_fill+3], 'little')
    assert initialized_size in (len(d) - segments[-1]*0x10 - header, len(d) - segments[-1]*0x10 - header-2)
    uninitialized_size = int.from_bytes(d[uninitialized_fill+4:uninitialized_fill+6], 'little') - initialized_size
    dereferencing = [b'\xbf', b'\xa1', b'\x8b\x1e', b'\xa3', b'\xc4\x1e', b'\xff\x36', b'\x89\x1e', b'\x8c\x06', b'\x8b\x16', b'\x89\x16', b'\x3b\x06', b'\x29\x06', b'\x3b\x16', b'\x19\x16']
    system_break_shift, = find_all(d, [0x8b, 0x56, 8, 3, 6, None, None, 0x83, 0xd2, 0, 0x8b, 0xc8, 0x81, 0xc1, 0, 1, 0x83, 0xd2, 0])
    system_break_address = int.from_bytes(d[system_break_shift+5:system_break_shift+7], 'little')
    system_break = int.from_bytes(d[system_break_address+segments[-1]*0x10+header:system_break_address+segments[-1]*0x10+header+2], 'little')
    assert system_break == initialized_size + uninitialized_size

    replaces = []
    ds = d[header + segments[-1]*0x10:]
    ds_size = len(ds)
    ds = ljust(ds, system_break, b'www.old-games.ru.')
    required_space = 0
    for t in translation:
        if t['source'] == binary:
            if not t['russian'].startswith('FIXME ') and t['russian'] != t['english']:
                references_segments = [x['segment'] for x in references.get((binary, t['offset']), [])]

                if len(t['russian']) <= len(t['english']):
                    message = t['russian'].encode('cp866').ljust(len(t['english']), b'\x00')
                    replaces.append((t['offset'], len(message), message))
                    replaced += 1

                elif t['offset'] > header + segments[-1]*0x10:
                    rr = references.get((binary, t['offset']), [])
                    for r in rr:
                        assert int.from_bytes(d[r['origin']:r['origin']+2], 'little') == t['offset'] - header - segments[-1]*0x10
                        replaces.append((r['origin'], 2, len(ds).to_bytes(2, 'little')))

                    ds.extend(t['russian'].encode('cp866') + b'\x00')

                    replaced += bool(rr)
                    added += 1

                elif all(map(lambda x: isinstance(x, int), references_segments)):
                    print(f'String {repr(t["russian"])} can be moved!')

            else:
                missing += 1

    for o, l, t in replaces: # TODO Эта штука нужна до тех пор пока есть несовместимые замены и она скрывает эти ошибки.
        assert len(t) == l
        d[o:o+l] = t

    ds[system_break_address:system_break_address+2] = len(ds).to_bytes(2, 'little')
    ds.extend(b'\x00' * ((len(ds) - ds_size + 0x1ff) // 0x200 * 0x200 - len(ds) + ds_size))
    assert (len(ds) - ds_size) % 0x200 == 0
    data_space = (len(ds) - ds_size) // 0x200
    print(f'{binary} — adding {data_space*0x200 + len(code_block)} bytes for {len(functions)} functions and {added} strings')
    d[header + segments[-1]*0x10:] = ds

    for f, (function_cs, function_ip, size) in functions.items():
        address = function_cs*0x10 + function_ip
        relocs[:] = [(o, s, l, v) for o, s, l, v in relocs if not v or o+s*0x10 >= address+size or o+s*0x10 < address-1]
        replace(d, header+address, jump(0, function_address[f], function_cs, function_ip).ljust(size, b'\x00'))

    assert set(d[relocs_base+4*relocs_size:header]) == {0}
    assert header - relocs_base >= len(relocs)*4

    for i, (offset, segment, local, vanilla) in enumerate(relocs):
        if not local:
            if vanilla:
                array = d
                array_base = header
            else:
                array = code_block
                array_base = 0
            assert offset < 0x10000
            x = offset+segment*0x10
            value = int.from_bytes(array[array_base+x:array_base+x+2], 'little')
            value += space*0x20
            assert value + 0x10 < 0x10000
            array[array_base+x:array_base+x+2] = value.to_bytes(2, 'little')
        if vanilla:
            segment += space*0x20
            assert segment < 0x10000
        d[relocs_base+i*4:relocs_base+i*4+2] = offset.to_bytes(2, 'little')
        d[relocs_base+i*4+2:relocs_base+i*4+4] = segment.to_bytes(2, 'little')

    for i in range(len(relocs), relocs_size):
        d[relocs_base+i*4:relocs_base+i*4+4] = b'\x00'*4

    pages += space + data_space
    d[6:8] = len(relocs).to_bytes(2, 'little')
    cs += space*0x20
    assert cs + 0x10 < 0x10000
    d[0x16:0x18] = cs.to_bytes(2, 'little')
    ss += (space+data_space)*0x20
    assert ss + 0x10 < 0x10000
    d[0x0e:0x10] = ss.to_bytes(2, 'little')
    d[4:6] = pages.to_bytes(2, 'little')
    d[0x0a:0x0c] = (max(0, int.from_bytes(d[0x0a:0x0c], 'little') - data_space*0x20)).to_bytes(2, 'little')
    d[0x0c:0x0e] = (max(0, int.from_bytes(d[0x0c:0x0e], 'little') - data_space*0x20)).to_bytes(2, 'little')

    d = d[:header] + code_block + d[header:]

    checksum = (checksum - sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) + original_checksum) & 0xffff
    d[0x12:0x14] = checksum.to_bytes(2, 'little')
    assert sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) & 0xffff == original_checksum

    with open(f'{output_directory}/{binary}', 'wb') as f:
        f.write(d)

    print(f'Written {binary}, {binascii.crc32(d) & 0xffffffff:08x}')

print(f'Missing strings: {missing} out of {len(translation)} — {100*missing/len(translation):.1f}%')
print(f'Replaced strings: {replaced} out of {len(translation)-missing} — {100*replaced/(len(translation)-missing):.1f}%')
