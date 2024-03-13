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

os.chdir(output_directory)
with open('U6.CH', 'wb') as f:
    f.write(d[:1024] + g[1536:1920] + e[1408:1792] + g[1920:] + g[1576:1584] + bytes((x >> 1 for x in g[1096:1104])) + e[1936:] + d[1024:])

assert s[:4] == b'\x08\x00\x0f\x00' # Looks like character dimensions.

for i, (lo, hi, size) in enumerate(zip(s[0x104:0x204], s[0x204:0x304], s[4:0x104])):
    offset = hi*0x100+lo
    end = offset + size*8

hi = s[0x204:0x304]
for i in range(0xa24, 0xa54):
    s[i] = 0x0f
with open('U6.SET', 'wb') as f:
    f.write(s)

# FIXME patch U6.SET

# FIXME also patch keyboard driver
