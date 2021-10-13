import os
from pathlib import Path
import re

from typing import List

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


def check_file_is_empty(file: Path, ignore_patterns: List[str] = [], ignore_strings: List[str] = []):
    if ignore_patterns or ignore_strings:
        ignore_re = re.compile(
            '|'.join([f'({patt})' for patt in ignore_patterns] + [f'({re.escape(s)})' for s in ignore_strings])
        )
        check_for_ignore = True
    else:
        check_for_ignore = False

    with open(file, 'r') as f:
        for line in f:
            if check_for_ignore and ignore_re.match(line):
                continue
            raise FilesCheckFailed(f"{file.name} contains unignored strings: {line}\n\tand maybe more...")
