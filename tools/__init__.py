import subprocess


def get_sha():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, universal_newlines=True, check=True)
        return r.stdout.rstrip()
    except Exception:
        return None
