import collections
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import tools
import tools.archive
import tools.conversation
import tools.file
import tools.lzw


patch_language = sys.argv[1] if len(sys.argv) >= 2 else 'russian'
conversation_language = sys.argv[2] if len(sys.argv) >= 3 else 'russian'
assert patch_language in ('russian', 'english')
assert conversation_language in ('russian', 'english')

with tempfile.TemporaryDirectory() as d:
    subprocess.run(['python3', '-m', 'tools.patch', d, patch_language], check=True) # FIXME switch to function
    # FIXME exepack
    subprocess.run(['python3', '-m', 'tools.symbols', d], check=True) # FIXME switch to function

    # FIXME get rid of tempfile

    for name in tools.get_compressed_files():
        with open(tools.get_path(name, d), 'rb') as f:
            data = tools.lzw.compress(f.read())
        with open(os.path.join(d, name), 'wb') as f:
            f.write(data)

    conversations = collections.defaultdict(dict)
    conversations_path = os.path.join(tools.get_script_path(), 'conversations')
    for character in sorted(os.listdir(conversations_path)):
        path = os.path.join(conversations_path, character)
        with open(path, 'r') as f:
            script = f.read()
        source, index, data = tools.conversation.encode(script, conversation_language, 2)
        conversations[source][index] = data

    for name in tools.get_archive_files():
        if name in ('CONVERSE.A', 'CONVERSE.B'):
            data = [None]*(max(conversations[name]) + 1)
            for index, item in conversations[name].items():
                data[index] = item
            tools.file.write(os.path.join(d, name), tools.archive.pack(data))

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

    existing_files = set(os.listdir(d))
    recursive_copy('original', d)

    sha = tools.get_sha()
    sha = f'-{sha}' if sha else ''

    patch_mode = f'[patch={patch_language}]' if patch_language != 'russian' else ''
    conversation_mode = f'[conversation={conversation_language}]' if conversation_language != 'russian' else ''
    basename = f'UltimaVI-ru{sha}{patch_mode}{conversation_mode}'
    name = f'{basename}.zip'

    print(f'Writing {name}')
    with zipfile.ZipFile(name, 'w') as f:
        for n in sorted(existing_files):
            f.write(os.path.join(d, n), os.path.join(basename, n))

    if outputs := os.environ.get('GITHUB_OUTPUT', None):
        with open(outputs, 'a') as f:
            f.write(f'name={name}\nbasename={basename}\n')
