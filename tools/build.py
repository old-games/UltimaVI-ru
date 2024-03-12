import os
import shutil
import subprocess
import tempfile
import zipfile

import tools


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with tempfile.TemporaryDirectory() as d:
    subprocess.run(['python3', '-m', 'tools.patch'], cwd=d, check=True)
    subprocess.run(['python3', '-m', 'tools.symbols'], cwd=d, check=True)

    existing_files = set(os.listdir(d))
    print(existing_files)
    for e in os.scandir('original'):
        if e.name not in existing_files:
            shutil.copy(e.path, f'{d}/{e.name}')
            existing_files.add(e.name)

    sha = tools.get_sha()
    sha = f'-{sha}' if sha else ''

    with zipfile.ZipFile(f'{output_directory}/UltimaVI-ru{sha}.zip', 'w') as f:
        for n in sorted(existing_files):
            f.write(f'{d}/{n}', f'UltimaVI-ru{sha}/{n}')
