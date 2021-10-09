import os
from pathlib import Path

from .exceptions import FilesCheckFailed


def check_particle_file_contents(particle_file: Path):
    with open(particle_file, 'rb') as f:
        pos = f.seek(-2, os.SEEK_END)
        char = None
        while pos > 0 and char != b'E':
            char = f.read(1)
            pos = f.seek(-2, os.SEEK_CUR)
        if char == b'E':
            f.seek(-2, os.SEEK_CUR)  # went -2 in the last while, again -2 to capture 4 bytes of RUNE
            word = f.read(4)
            if word == b'RUNE':
                return
    raise FilesCheckFailed(f"{particle_file.name} doesn't contain RUNE at the end")
