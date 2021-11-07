import pytest
from pytest import param
from pathlib import Path

from tasdmc.steps.utils import check_particle_file_contents, FilesCheckFailed


@pytest.mark.parametrize(
    "pre_pad_kb, post_pad_kb",
    [
        param(3, 3, id="RUNE padded"),
        param(4, 0, id="RUNE right at the end"),
        param(0, 5, id="RUNE at the start"),
        param(3, 2.999, id="RUNE at the block edge"),
    ],
)
def test_particle_file_check(pre_pad_kb, post_pad_kb, temp_file: Path):
    with open(temp_file, 'wb') as f:
        f.write(b"\0" * int(pre_pad_kb * 1024))
        f.write(b"RUNE")
        f.write(b"\0" * int(post_pad_kb * 1024))
    check_particle_file_contents(temp_file)


def test_particle_file_check_fails(temp_file: Path):
    with open(temp_file, 'wb') as f:
        f.write((b"\0" * 1024 * 3) + b'E' + (b"\0" * 1024 * 2))
    with pytest.raises(FilesCheckFailed):
        check_particle_file_contents(temp_file)
