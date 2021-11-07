import os
from pathlib import Path
import re
import hashlib
from functools import wraps

from typing import List, Any, Callable, TypeVar, BinaryIO, Generator, Iterable, TypeVar, Tuple

from tasdmc.c_routines_wrapper import list_events_in_dst_file
from .exceptions import FilesCheckFailed


def _read_file_backwards(f: BinaryIO, block_size: int = 1024) -> Generator[bytes, None, None]:
    f.seek(0, os.SEEK_END)
    file_length = f.tell()
    end_offset = 0
    while end_offset < file_length:
        end_offset += block_size
        if end_offset > file_length:
            block_size -= end_offset - file_length
            if block_size == 0:
                break
            end_offset = file_length
        f.seek(-end_offset, os.SEEK_END)
        yield f.read(block_size)[::-1]


def _in_pairs(iterable: Iterable[bytes]) -> Generator[Tuple[bytes, bytes], None, None]:
    iterator = iter(iterable)
    prev = next(iterator)
    for item in iterator:
        yield prev, item
        prev = item


def check_particle_file_contents(particle_file: Path):
    with open(particle_file, 'rb') as f:
        for last, second_to_last in _in_pairs(_read_file_backwards(f, block_size=1024)):
            if b"E" not in last:
                continue
            else:
                if b"RUNE" in (last + second_to_last)[::-1]:
                    return

    if b"RUNE" in second_to_last[::-1]:
        return

    raise FilesCheckFailed(f"{particle_file.name} doesn't contain RUNE bytes at the end")


def check_file_is_empty(file: Path, ignore_patterns: List[str] = [], ignore_strings: List[str] = []):
    if ignore_patterns or ignore_strings:
        ignore_re = re.compile(
            '|'.join([f'({patt})' for patt in ignore_patterns] + [f'(^{re.escape(s)}$)' for s in ignore_strings])
        )
        check_for_ignore = True
    else:
        check_for_ignore = False

    with open(file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if check_for_ignore and ignore_re.match(line):
                continue
            raise FilesCheckFailed(f"{file.name} contains unignored strings:\n\t'{line}'\n\tand maybe more...")


def check_last_line_contains(file: Path, must_contain: str):
    with open(file, 'r') as f:
        last_line = ''
        for line in f:
            if line.strip():
                last_line = line
        if must_contain not in last_line:
            raise FilesCheckFailed(f"{file} does not contain '{must_contain}' in the last line ('{last_line}')")


def check_dst_file_not_empty(file: Path):
    return len(list_events_in_dst_file(file)) > 0


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


CheckFnArgs = TypeVar("CheckFnArgs")


def passed(check_fn: Callable[[CheckFnArgs], None]) -> Callable[[CheckFnArgs], bool]:
    """Wrapper/decorator to call any check function from above but return success flag istead of raising an exception

    >>> flag = passed(check_file_is_empty)(my_file, ignored_lines=['smth'])
    """

    @wraps(check_fn)
    def wrapped(*args, **kwargs):
        try:
            check_fn(*args, **kwargs)
            return True
        except FilesCheckFailed:
            return False

    return wrapped
