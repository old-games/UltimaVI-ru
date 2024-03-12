import os


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('original/U6.CH', 'rb') as f:
    d = f.read()

with open('tools/cp866-8x8', 'rb') as f:
    e = f.read()

with open('tools/atari-st-8x8', 'rb') as f:
    g = f.read()

os.chdir(output_directory)
with open('U6.CH', 'wb') as f:
    f.write(d[:1024] + g[1536:1920] + e[1408:1792] + g[1920:] + g[1576:1584] + bytes((x >> 1 for x in g[1096:1104])) + e[1936:] + d[1024:])

# FIXME also patch keyboard driver
