import os


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('unpacked/GAME.EXE', 'rb') as f:
    d = bytearray(f.read())

checksum = int.from_bytes(d[0x12:0x14], 'little')
assert sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) & 0xffff == 0xffff
space = 3
pages = int.from_bytes(d[4:6], 'little')
cs = int.from_bytes(d[0x16:0x18], 'little')
ss = int.from_bytes(d[0x0e:0x10], 'little')
relocs = int.from_bytes(d[6:8], 'little')
header = int.from_bytes(d[8:0x0a], 'little') * 0x10
relocs_base = int.from_bytes(d[0x18:0x1a], 'little')
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
pages += space
cs += space*0x20
assert cs + 0x10 < 0x10000
d[0x16:0x18] = cs.to_bytes(2, 'little')
ss += space*0x20
assert ss + 0x10 < 0x10000
d[0x0e:0x10] = ss.to_bytes(2, 'little')
d[4:6] = pages.to_bytes(2, 'little')

assert d[0xb203:0xb206] == b'\x0d\x80\x00'
assert d[0xabb5:0xabba] == b'\x81\x4e\x06\x80\x00'

d[0xb204:0xb206] = b'\x00\x01'
d[0xabb8:0xabba] = b'\x00\x01'

def replace(d, o, s, x):
    assert len(x) == s, f'{len(x)} != {s}'
    d[o:o+s] = x

replace(d, 0x310b4, 0x2e, 'ХУЙ С РУНАМИ <ABCD>!!! Функция: %d, о: %d, ф: '.encode('cp866'))

d = d[:header] + b'\x00'*space*0x200 + d[header:]

checksum = (checksum - sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) + 0xffff) & 0xffff
d[0x12:0x14] = checksum.to_bytes(2, 'little')
assert sum(map(lambda x: x[1]*0x100+x[0], zip(d[::2], d[1::2]))) & 0xffff == 0xffff

os.chdir(output_directory)
with open('GAME.EXE', 'wb') as f:
    f.write(d)

# TODO: check / fix tolower / toupper / isalpha etc?
# TODO: игра буферизует символы в отдельном массиве перед выводом для того чтобы правильно разбивать на строки и они становятся байтами. Это нужно переделать.
