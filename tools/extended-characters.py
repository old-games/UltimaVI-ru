import os


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('unpacked/GAME.EXE', 'rb') as f:
    d = bytearray(f.read())

assert d[0xb203:0xb206] == b'\x0d\x80\x00'
assert d[0xabb5:0xabba] == b'\x81\x4e\x06\x80\x00'

d[0xb204:0xb206] = b'\x00\x01'
d[0xabb8:0xabba] = b'\x00\x01'

os.chdir(output_directory)
with open('GAME.EXE', 'wb') as f:
    f.write(d)

# TODO: check / fix tolower / toupper
# TODO: игра буферизует символы в отдельном массиве перед выводом для того чтобы правильно разбивать на строки и они становятся байтами. Это нужно переделать.
