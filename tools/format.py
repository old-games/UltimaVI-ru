import re
import subprocess
import sys
import tempfile


def unhex(string):
    if string.startswith('0x'):
        return int(string[2:], 16)
    else:
        return int(string)


path = sys.argv[1]
start = unhex(sys.argv[2])
end = unhex(sys.argv[3])
origin = unhex(sys.argv[4])

assert start < end

with open(path, 'rb') as f:
    data = f.read()

with tempfile.TemporaryDirectory() as d:
    with open(f'{d}/block.bin', 'wb') as f:
        f.write(data[start:end])
    r = subprocess.run(['ndisasm', '-b', '16', '-o', str(origin), f'{d}/block.bin'], stdout=subprocess.PIPE, universal_newlines=True, check=True)

input_lines = r.stdout.splitlines()

fixups = {}
labels = set()
for line in input_lines:
    (address, _, instruction, arguments), = re.findall('([0-9A-F]+) +([0-9A-F]+) +([^ ]+)(?: +(.*)|$)', line)
    if instruction in ('call', 'jmp') and ':' in arguments:
        fixups[int(address, 16)] = len(fixups)
    elif (instruction[0] == 'j' or instruction == 'call') and '[' not in arguments:
        if arguments.startswith('short '):
            arguments = ' '.join(arguments.split(' ')[1:])
        assert arguments.startswith('0x')
        labels.add(unhex(arguments))


def add_empty():
    if not result[-1].endswith(':'):
        result.append('')


result = []
result.append('bits 16')
result.append('')
result.append(f'global sub_{origin:04x}')
if fixups:
    result.append('')
for f in fixups.values():
    result.append(f'global fixmeup{f}')
result.append('')
result.append('section CODE')
result.append('')
result.append(f'; python3 -m tools.format {path} {hex(start)} {hex(end)} {hex(origin)}')
result.append('')
result.append(f'sub_{origin:04x}:')

lines = []
for line in input_lines:
    (address, _, instruction, arguments), = re.findall('([0-9A-F]+) +([0-9A-F]+) +([^ ]+)(?: +(.*)|$)', line)
    address = int(address, 16)
    if address in labels:
        add_empty()
        result.append(f'loc_{address:04x}:')
    if address in fixups:
        add_empty()
        result.append(f'fixmeup{fixups[address]}: ; far call by absolute direct address')
    elif (instruction[0] == 'j' or instruction == 'call') and '[' not in arguments:
        if arguments.startswith('short '):
            arguments = ' '.join(arguments.split(' ')[1:])
        assert arguments.startswith('0x')
        arguments = f'loc_{unhex(arguments):04x}'
    result.append(f'{" "*8}{instruction.ljust(7)} {", ".join(arguments.split(","))}')

assert instruction in ('ret', 'retf')

for line in result:
    print(line)
