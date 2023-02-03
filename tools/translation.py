import json
import os


os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('tools/translation.json') as f:
    t = json.loads(f.read())

for i in t:
    assert set(i.keys()) == {'source', 'offset', 'english', 'russian'}
    assert i['source'] in {'GAME.EXE', 'END.EXE', 'INSTALL.EXE', 'U.EXE', 'ULTIMA6.EXE'}
    assert isinstance(i['offset'], int)
