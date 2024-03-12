import os
import subprocess


def get_sha():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True, check=True)
        return r.stdout.rstrip()
    except Exception:
        return None


def get_binary_path(binary):
    path = f'unpacked/{binary}'
    if os.path.isfile(path):
        return path
    else:
        return f'original/{binary}'
