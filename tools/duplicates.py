import json
import os
import random
import sys


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('patches/references.json') as f:
    references = {(x['source'], x['offset']): x['references'] for x in json.loads(f.read())}

with open('patches/bad-references.json') as f:
    br = json.loads(f.read())

for x in br:
    bad = set(x['bad-references'])
    references[(x['source'], x['offset'])] = [
        y
        for y in references[(x['source'], x['offset'])]
        if y['origin'] not in bad
    ]

for k, v in references.items():
    if len(v) > 1:
        print('WARNING', k[0], hex(k[1]), len(v), 'references:', ', '.join((hex(x['origin']) for x in v)))

if sys.argv[1:] in (['--fix'], ['--fix-half'], ['--fix-tenth']):
    added = set()
    if sys.argv[1:] == ['--fix-half']:
        threshold = 0.5
    elif sys.argv[1:] == ['--fix-tenth']:
        threshold = 0.1
    else:
        threshold = 1.0

    for k, v in references.items():
        if len(v) > 1:
            for b in br:
                if b['source'] == k[0] and b['offset'] == k[1]:
                    found = b
                    break
            else:
                found = {'source': k[0], 'offset': k[1], 'bad-references': [x['origin'] for x in v]}
                br.append(found)

            for x in v:
                if random.random() <= threshold:
                    found['bad-references'].append(x['origin'])
                    added.add((k[0], k[1], x['origin']))
            found['bad-references'] = sorted(found['bad-references'])

    print('Added:', sorted(added))
    br = sorted(br, key=lambda x: (x['source'], x['offset'])) 
    with open('patches/bad-references.json', 'w') as f:
        f.write(json.dumps(br, indent=4))
