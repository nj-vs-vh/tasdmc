import os
from pathlib import Path
import re
import hashlib

from typing import List, Any

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
            raise FilesCheckFailed(f"{file.name} contains unignored strings:\n\t{line.strip()}\n\tand maybe more...")


def check_last_line_contains(file: Path, must_contain: str):
    with open(file, 'r') as f:
        line = ''
        for line in f:
            pass
        if must_contain not in line:
            raise FilesCheckFailed(f"{file} does not contain '{must_contain}' in the last line")


def file_contents_hash(file_path: Path, hasher_name: str = 'md5') -> str:
    hasher = hashlib.new(hasher_name)
    file_size = file_path.stat().st_size
    with open(file_path, 'rb') as f:
        if file_size < 1024 * 1024:  # for files smaller than Mb hash is calculated directly
            hasher.update(f.read())
        else:
            # for large files, read several blocks spread across file and use only them in hash
            n_reads = 1024
            block_size = 1024
            jump_size = file_size // n_reads
            for _ in range(n_reads - 1):
                hasher.update(f.read1(block_size))
                f.seek(jump_size, os.SEEK_CUR)
            # last block is read from the end
            f.seek(-(block_size + 1), os.SEEK_END)
            hasher.update(f.read1(block_size))
    return hasher.hexdigest()


def concatenate_and_hash(contents: List[Any], delimiter: str = ':', hasher_name: str = 'md5') -> str:
    concat_strings = delimiter.join([str(s) for s in contents])
    hasher = hashlib.new(hasher_name, data=concat_strings.encode('utf-8'))
    return hasher.hexdigest()
