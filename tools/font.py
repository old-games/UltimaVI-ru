import sys


with open(sys.argv[1], 'rb') as f:
    x = f.read()

for i in range((len(x) + 31) // 32):
    if i % 8 == 0:
        print(f'{i // 8 * 32:02X}')

    for j in range(256):
        c = i // 8 * 32 + j // 8
        print(' x'[bool(x[c*8+(i % 8)] & (1 << (7-j%8)))], end='')
    print()
