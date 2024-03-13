import os
import sys


ext = os.path.splitext(sys.argv[1])[1]
if ext == '.CH':
    with open(sys.argv[1], 'rb') as f:
        x = f.read()

    width = 9
    result = []
    for r in range(len(x) // 128):
        result.append([f'{r*0x10:02X}'])
        for k in range(4):
            result.append([' ']*width*16)

    for i in range(len(x) // 128):
        for k in range(8):
            for j in range(16):
                for l in range(8):
                    c = i * 16 + j
                    C = x[c*8+k] & (1 << (7-l%8))
                    if C:
                        r = result[1+k//2+i*5][j*width+l]
                        if k % 2 == 0:
                            result[1+k//2+i*5][j*width+l] = '▀'
                        elif r == ' ':
                            result[1+k//2+i*5][j*width+l] = '▄'
                        else:
                            result[1+k//2+i*5][j*width+l] = '█'

    for l in result:
        print(''.join(l))

elif ext == '.SET':
    with open(sys.argv[1], 'rb') as f:
        s = f.read()

    width = max(s[4:0x104]) + 1
    result = []
    for r in range(16):
        result.append([f'{r*0x10:02X}'])
        for k in range(4):
            result.append([' ']*width*16)

    for i, (lo, hi, size) in enumerate(zip(s[0x104:0x204], s[0x204:0x304], s[4:0x104])):
        offset = hi*0x100+lo
        assert offset >= 0x304
        end = offset + size*8

        for j in range(8):
            for k in range(size):

                c = s[offset+j*size+k]
                assert c in (0, 15)
                if c:
                    r = result[1+j//2+i//16*5][i%16*width+k]
                    if j % 2 == 0:
                        result[1+j//2+i//16*5][i%16*width+k] = '▀'
                    elif r == ' ':
                        result[1+j//2+i//16*5][i%16*width+k] = '▄'
                    else:
                        result[1+j//2+i//16*5][i%16*width+k] = '█'

    for l in result:
        print(''.join(l))
