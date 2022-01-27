import pytest

from pathlib import Path
from dataclasses import dataclass, field
from itertools import chain

from typing import List

from tasdmc.steps.base import Files, files_dataclass


@files_dataclass
class DummyFiles(Files):
    @property
    def must_exist(self) -> List[Path]:
        return []


def test_files_must_be_dataclasses():
    class NonDataclassFiles(Files):
        pass

    with pytest.raises(TypeError):
        NonDataclassFiles()


def test_all_files_property():
    @files_dataclass
    class NestedFiles(DummyFiles):
        smth: Path = Path('dummy')

    @files_dataclass
    class FilesWithPaths(DummyFiles):
        file1: Path
        file2: Path

        extra_arg: int = 1
        extra_arg2: bool = False
        extra_list_arg: List[str] = field(default_factory=lambda: ['a', 'b', 'c'])
        member_files: Files = NestedFiles()

    all_files = [Path('a/b/c'), Path('d/e/f')]
    assert FilesWithPaths(*all_files).all_files == all_files

    @files_dataclass
    class FilesWithPathLists(DummyFiles):
        files1: List[Path]
        files2: List[Path]

        extra_arg: int = 1
        extra_arg2: bool = False
        extra_list_arg: List[str] = field(default_factory=lambda: ['a', 'b', 'c'])
        member_files: Files = NestedFiles()

    path_lists = [[Path('a/b/c'), Path('d/e/f')], [Path('1/2/3'), Path('4/5/6'), Path('7/8/9')]]
    assert set(FilesWithPathLists(*path_lists).all_files) == set(chain.from_iterable(path_lists))

    @files_dataclass
    class FilesWithBoth(DummyFiles):
        file1: Path
        files2: List[Path]
        files3: List[Path]

        extra_arg: int = 1
        extra_arg2: bool = False
        extra_list_arg: List[str] = field(default_factory=lambda: ['a', 'b', 'c'])
        member_files: Files = NestedFiles()

    path = Path("hello")
    path_lists = [[Path('a/b/c'), Path('d/e/f')], [Path('1/2/3'), Path('4/5/6'), Path('7/8/9')]]
    assert set(FilesWithBoth(path, *path_lists).all_files) == set(chain.from_iterable(path_lists)).union({path})
