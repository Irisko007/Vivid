#!/usr/bin/env python3
"""Create the portable Linux source bundle and its download checksum."""
import hashlib
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'dist'
OUTPUT.mkdir(exist_ok=True)
archive = OUTPUT / 'vivid-linux.tar.gz'

def include(info):
    if '__pycache__' in info.name or info.name.endswith(('.pyc', '.pyo')):
        return None
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    return info

with tarfile.open(archive, 'w:gz') as bundle:
    for name in ['vivid', 'scripts', 'packaging', 'docs', 'README.md', 'README.ru.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md', 'pyproject.toml', 'MANIFEST.in', 'default.nix', 'shell.nix', 'run.sh', 'install.sh', 'set-default.sh']:
        bundle.add(ROOT / name, arcname='vivid/' + name, filter=include)
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(OUTPUT / 'SHA256SUMS').write_text(f'{checksum}  vivid-linux.tar.gz\n')
print(archive)
