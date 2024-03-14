import json
import os

import tools


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('tools/references.json') as f:
    references = {(x['source'], x['offset']): x['references'] for x in json.loads(f.read())}

with open('tools/bad-references.json') as f:
    for x in json.loads(f.read()):
        bad = set(x['bad-references'])
        references[(x['source'], x['offset'])] = [
            y
            for y in references[(x['source'], x['offset'])]
            if y['origin'] not in bad
        ]

for k, v in references.items():
    if len(v) > 1:
        print('WARNING', k[0], k[1], len(v), 'references')
