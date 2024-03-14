import os
import shutil
import subprocess
import tempfile
import zipfile

import tools
import tools.lzw


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with tempfile.TemporaryDirectory() as d:
    subprocess.run(['python3', '-m', 'tools.patch'], cwd=d, check=True)
    # FIXME exepack
    subprocess.run(['python3', '-m', 'tools.symbols'], cwd=d, check=True)

    for name in tools.get_compressed_files():
        with open(tools.get_path(name, d), 'rb')  as f:
            data = tools.lzw.compress(f.read())
        with open(os.path.join(d, name), 'wb') as f:
            f.write(data)

    existing_files = set(os.listdir(d))
    for e in os.scandir('original'):
        if e.name not in existing_files:
            shutil.copy(e.path, os.path.join(d, e.name))
            existing_files.add(e.name)

    sha = tools.get_sha()
    sha = f'-{sha}' if sha else ''

    with zipfile.ZipFile(os.path.join(output_directory, f'UltimaVI-ru{sha}.zip'), 'w') as f:
        for n in sorted(existing_files):
            f.write(os.path.join(d, n), os.path.join(f'UltimaVI-ru{sha}', n))
