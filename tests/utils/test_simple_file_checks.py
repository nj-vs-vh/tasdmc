import pytest

from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains, FilesCheckFailed


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


def test_last_line_contains_check(temp_file):
    with open(temp_file, 'w') as f:
        f.write("1\n")
        f.write("2\n")
        f.write("last line!")

    for i in range(2):
        check_last_line_contains(temp_file, must_contain='last line!')
        check_last_line_contains(temp_file, must_contain='line')
        check_last_line_contains(temp_file, must_contain='!')

        with open(temp_file, 'a') as f:  # checks must pass no matter how much empty lines follow the last
            f.write('\n' + ' ' * i)


def test_last_line_contains_check_fails(temp_file):
    with open(temp_file, 'w') as f:
        f.write("1\n")
        f.write("last line!\n")
        f.write("this is error!\n\n")

    with pytest.raises(FilesCheckFailed):
        check_last_line_contains(temp_file, must_contain='last line')
