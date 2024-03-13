import os
import sys


ext = os.path.splitext(sys.argv[1])[1]
if ext == '.CH':
    with open(sys.argv[1], 'rb') as f:
        x = f.read()

    for i in range((len(x) + 31) // 32):
        if i % 8 == 0:
            print(f'{i // 8 * 32:02X}')

        for j in range(256):
            c = i // 8 * 32 + j // 8
            print(' █'[bool(x[c*8+(i % 8)] & (1 << (7-j%8)))], end='')
        print()

elif ext == '.SET':
    with open(sys.argv[1], 'rb') as f:
        s = f.read()

    width = max(s[4:0x104]) + 1
    result = []
    for r in range(8):
        result.append([f'{r*0x20:02X}'])
        for k in range(8):
            result.append([' ']*width*32)

    for i, (lo, hi, size) in enumerate(zip(s[0x104:0x204], s[0x204:0x304], s[4:0x104])):
        offset = hi*0x100+lo
        assert offset >= 0x304
        end = offset + size*8

        for j in range(8):
            for k in range(size):
                c = s[offset+j*size+k]
                assert c in (0, 15)
                if c:
                    result[1+j+i//32*9][i%32*width+k] = '█'

    for l in result:
        print(''.join(l))
