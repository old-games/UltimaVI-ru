import os

import tools


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open(tools.get_path('U6.CH'), 'rb') as f:
    d = f.read()

with open(tools.get_path('U6.SET'), 'rb') as f:
    s = bytearray(f.read())

with open('tools/cp866-8x8', 'rb') as f:
    e = f.read()

with open('tools/atari-st-8x8', 'rb') as f:
    g = f.read()

combined_font = d[:1024] + g[1536:1920] + e[1408:1792] + g[1920:] + g[1576:1584] + bytes((x >> 1 for x in g[1096:1104])) + e[1936:] + d[1024:]

os.chdir(output_directory)
with open('U6.CH', 'wb') as f:
    f.write(combined_font)

assert s[:4] == b'\x08\x00\x0f\x00' # Looks like character dimensions?

symbols_data = []
for i, (lo, hi, size) in enumerate(zip(s[0x104:0x204], s[0x204:0x304], s[4:0x104])):
    offset = hi*0x100+lo
    end = offset + size*8
    symbols_data.append(s[offset:end])

s = s[:0x304]

symbols = [
    *range(0x20),
    *range(0x80, 0x100),
]
for symbol in symbols:
    data = combined_font[symbol*8:symbol*8+8]
    left = 7
    right = 0
    for i in range(8):
        r = data[i]
        for k in range(8):
            if r & 1 << 7-k:
                left = min(left, k)
                right = max(right, k)
    width = 1 + max(0, right-left+1)
    y = bytearray([0]*width*8)
    for row in range(8):
        for col in range(1, width):
            k = left + col - 1
            r = data[row]
            if r & 1 << 7-k:
                y[row*width+col] = 0x0f
    symbols_data[symbol] = y

for i, data in enumerate(symbols_data):
    offset = len(s)
    assert len(data) % 8 == 0
    width = len(data) // 8
    s[4+i] = width
    s[0x104+i] = offset & 0xff
    s[0x204+i] = offset >> 8
    s += data

with open('U6.SET', 'wb') as f:
    f.write(s)

# TODO also patch keyboard driver :)
