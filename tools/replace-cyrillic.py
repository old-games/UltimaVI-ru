import os


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('original/U6.CH', 'rb') as f:
    d = f.read()

with open('tools/cp866-8x8', 'rb') as f:
    e = f.read()

os.chdir(output_directory)
with open('U6.CH.new', 'wb') as f:
    f.write(d[:1024] + e[1024:] + d[1024:])
