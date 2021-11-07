import pytest
from pathlib import Path
from random import randint

from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains, FilesCheckFailed


CUR_DIR = Path(__file__).parent


@pytest.fixture
def temp_file() -> Path:
    fname = CUR_DIR / f"testing.{randint(0, 10 ** 6)}"
    fname.touch()
    yield fname
    fname.unlink()


def test_empty_file_check_ok(temp_file):
    check_file_is_empty(temp_file)
    with open(temp_file, 'w') as f:
        f.write("ignored\n")
        f.write("also ignored string\n")
    check_file_is_empty(temp_file, ignore_strings=['ignored', 'also ignored string'])
    check_file_is_empty(temp_file, ignore_patterns=[r'.*ignored.*'])


def test_empty_file_check_ignores_empty_lines(temp_file):
    with open(temp_file, 'w') as f:
        f.write("\n\n\n\n")
    check_file_is_empty(temp_file)


def test_empty_file_check_fails(temp_file):
    with open(temp_file, 'w') as f:
        f.write("one two\n")
        f.write("three four\n")
    with pytest.raises(FilesCheckFailed):
        check_file_is_empty(temp_file)
        check_file_is_empty(temp_file, ignore_strings=["one two"])
        check_file_is_empty(temp_file, ignore_patterns=[r".*two"])
