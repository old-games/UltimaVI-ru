import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import tools
import tools.lzw


mode = sys.argv[1] if len(sys.argv) == 2 else 'russian'
assert mode in ('russian', 'english')

output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with tempfile.TemporaryDirectory() as d:
    if mode == 'russian':
        subprocess.run(['python3', '-m', 'tools.patch'], cwd=d, check=True)
        # FIXME exepack
        subprocess.run(['python3', '-m', 'tools.symbols'], cwd=d, check=True)

    for name in tools.get_compressed_files():
        with open(tools.get_path(name, d), 'rb')  as f:
            data = tools.lzw.compress(f.read())
        with open(os.path.join(d, name), 'wb') as f:
            f.write(data)

    existing_files = set(os.listdir(d))

    def recursive_copy(source, destination, sub_directory=None):
        for e in os.scandir(source):
            if e.name not in existing_files:
                full_name = e.name if sub_directory is None else os.path.join(sub_directory, e.name)
                if e.is_file():
                    shutil.copy(e.path, os.path.join(destination, e.name))
                    existing_files.add(full_name)
                elif e.is_dir():
                    os.makedirs(os.path.join(destination, e.name))
                    recursive_copy(os.path.join(source, e.name), os.path.join(destination, e.name), sub_directory=full_name)

    recursive_copy('original', d)

    sha = tools.get_sha()
    sha = f'-{sha}' if sha else ''

    mode = f'-{mode}' if mode == 'english' else ''

    with zipfile.ZipFile(os.path.join(output_directory, f'UltimaVI-ru{mode}{sha}.zip'), 'w') as f:
        for n in sorted(existing_files):
            f.write(os.path.join(d, n), os.path.join(f'UltimaVI-ru{mode}{sha}', n))
