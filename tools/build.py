import os
import shutil
import subprocess
import tempfile
import zipfile


output_directory = os.getcwd()
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with tempfile.TemporaryDirectory() as d:
    subprocess.run(['python3', os.path.abspath('tools/patch.py')], cwd=d).check_returncode()
    subprocess.run(['python3', os.path.abspath('tools/replace-cyrillic.py')], cwd=d).check_returncode()

    existing_files = set(os.listdir(d))
    for e in os.scandir('original'):
        if e.name not in existing_files:
            shutil.copy(e.path, f'{d}/{e.name}')
            existing_files.add(e.name)

    r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True)
    sha = f'-{r.stdout.rstrip()}' if r.returncode == 0 else ''

    with zipfile.ZipFile(f'{output_directory}/UltimaIV-ru{sha}.zip', 'w') as f:
        for n in sorted(existing_files):
            f.write(f'{d}/{n}', f'UltimaIV-ru{sha}/{n}')
