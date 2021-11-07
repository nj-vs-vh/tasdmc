from abc import ABC
from pathlib import Path
from dataclasses import fields, is_dataclass
from functools import lru_cache

from typing import Optional, List, Any, Literal, get_args, get_origin

from tasdmc import fileio, config
from tasdmc.logs import input_hashes_debug
from ..exceptions import FilesCheckFailed
from ..utils import file_contents_hash, concatenate_and_hash


class Files(ABC):
    """Abstract class for storing info on any set of files serving as inputs/outputs of tasdmc steps.

    Subclassed by each step to incapsulate specific behavior and checks.
    """

    @property
    def all_files(self) -> List[Path]:
        """Simply all files in Files'. Since most subclasses are dataclasses, this can be inferred
        from Path-typed fields automatically.

        May be overriden by subclasses.
        """
        if not is_dataclass(self):
            raise TypeError(
                "Cannot automatically infer file paths for non-dataclass Files subclass "
                + f"{self.__class__.__name__}. Maybe override this property?"
            )

        def is_list_of_paths(t: Any):
            args = get_args(t)
            return get_origin(t) is List and len(args) == 1 and args[0] == Path

        all_file_paths: List[Path] = []
        for f in fields(self):
            value = self.__getattribute__(f.name)
            if f.type == Path or f.type == 'Path':
                all_file_paths.append(value)
            elif is_list_of_paths(f.type) or f.type == 'List[Path]':
                all_file_paths.extend(value)
        return all_file_paths

    def total_size(self, units: Literal['b', 'Kb', 'Mb', 'Gb']) -> int:
        """Total Files' size in specified units"""
        size_by_unit = {
            'b': 1,
            'Kb': 1024,
            'Mb': 1024 ** 2,
            'Gb': 1024 ** 3,
        }
        return sum([f.stat().st_size / size_by_unit[units] for f in self.all_files])

    def prepare_for_step_run(self):
        """Ensure that Files are ready to be created from scratch in a step.run(). For example, delete existing
        files if they can't be automatically overwritten during step run.

        May be overriden by subclasses.
        """
        pass

    # Files' validation methods

    @property
    def must_exist(self) -> List[Path]:
        """List of file Paths that must exist for Files to be a valid step output. May be overriden by subclasses."""
        return []

    def assert_files_are_ready(self):
        """Check Files if they are ready and raise FilesCheckFailes exception if there's a problem.

        Should not be overriden, but modified indirectly by overriding must_exist property and _check_contents method.
        """
        nonexistent_files = []
        for f in self.must_exist:
            if not f.exists():
                nonexistent_files.append(f)
        if nonexistent_files:
            raise FilesCheckFailed(
                "Following required files do not exist: \n"
                + "\n".join([f"\t{missing_file}" for missing_file in nonexistent_files])
            )
        else:
            self._check_contents()

    def files_were_produced(self) -> bool:
        """Returns bool value indicating if Files' were already produced."""
        try:
            self.assert_files_are_ready()
            return True
        except FilesCheckFailed:
            return False

    def _check_contents(self):
        """Check Files' contents in a specific way (e.g. checking for errors in stderr file, validating binary files).
        Must raise FilesCheckFailed on errors.

        Should be overriden by subclasses."""
        pass

    # methods for calculating Files' hash and storing it on disk for later check

    @property
    def to_be_hashed(self) -> Optional[List[Path]]:
        """Explicit list of file Paths that should be used to get Files' hash.

        If not overriden by a subclass and subclass is a dataclass, all Path and List[Path] fields are used.
        """
        return None

    @property
    def _to_be_hashed(self) -> List[Path]:
        if self.to_be_hashed is not None:
            return self.to_be_hashed
        else:
            return self.all_files

    @property
    def _stored_hash_path(self) -> Path:
        """Hash is stored in a file with class name and file paths' (not content!) hash"""
        paths_id = concatenate_and_hash(self._to_be_hashed)
        return fileio.input_hashes_dir() / f"{self.__class__.__name__}.{paths_id}"

    def _get_file_contents_hash(self, file: Path) -> str:
        if not file.exists():
            raise ValueError(
                f"Can't compute {self.__class__.__name__}'s contents hash, some files to be hashed do not exist"
            )
        return file_contents_hash(file, hasher_name='md5')

    @property
    def contents_hash(self) -> str:
        cached_attrname = '_contents_hash'
        try:
            return getattr(self, cached_attrname)
        except AttributeError:
            pass

        file_hashes = []
        for file in self._to_be_hashed:
            file_hashes.append(self._get_file_contents_hash(file))
        contents_hash = concatenate_and_hash(file_hashes)

        setattr(self, cached_attrname, contents_hash)
        return contents_hash

    def store_contents_hash(self):
        contents_hash = self.contents_hash
        with open(self._stored_hash_path, 'w') as f:
            f.write(contents_hash)

    def same_hash_as_stored(self) -> bool:
        stored_hash_path = self._stored_hash_path
        if not stored_hash_path.exists():
            if _input_hashes_log_enabled():
                input_hashes_debug(f"{stored_hash_path.name} has no stored hash, considering comparison FAILED")
            return False
        with open(stored_hash_path, 'r') as f:
            stored_hash = f.read()
        if _input_hashes_log_enabled():
            input_hashes_debug(
                f"{stored_hash_path.name} hash comparison "
                + (
                    "OK"
                    if self.contents_hash == stored_hash
                    else f"FAILED (actual hash: {self.contents_hash}; stored hash: {stored_hash})"
                )
            )
        return self.contents_hash == stored_hash


class NotAllRetainedFiles(Files):
    """Subclass of Files for cases when some of the files are not retained (for example, they are too big)"""

    @property
    def not_retained(self) -> List[Path]:
        """List of file Paths that can be removed after they have been used in pipeline. This should include
        temporary or very large files, unnecessary for the end result. May be overriden by subclasses.
        """
        return []

    def delete_not_retained_files(self):
        """Delete files that are not retained after pipeline end and create .deleted files in their place"""
        for f in self.not_retained:
            if f.exists():
                with open(_with_deleted_suffix(f), 'w') as del_f:
                    del_f.write(
                        f'{f}\nwas produced bytes and then deleted\n\n'
                        + f'its size was {f.stat().st_size} bytes\n\n'
                        + 'its contents hash was:\n'
                        + file_contents_hash(f)
                    )
                f.unlink()

    def _get_file_contents_hash(self, file: Path) -> str:
        if not file.exists():
            deleted_file = _with_deleted_suffix(file)
            if deleted_file.exists():
                with open(deleted_file, 'r') as df:
                    for line in df:
                        pass
                    if len(line) == 32:
                        return line
                    else:
                        raise ValueError(f"Can't recover {self.__class__.__name__}'s contents hash from .deleted file")
            else:
                raise ValueError(
                    f"Can't compute {self.__class__.__name__}'s contents hash, "
                    + "some files to be hashed do not exist"
                )
        return file_contents_hash(file, hasher_name='md5')

    def files_were_produced(self) -> bool:
        """Returns bool value indicating if Files' were already produced.

        This is not the same as assert_files_are_ready as it also checks for files that may have been deleted
        because they are listed in not_retained.
        """
        try_checking_contents = True
        for f in self.must_exist:
            if not f.exists():
                if f in self.not_retained and _with_deleted_suffix(f).exists():
                    try_checking_contents = False  # there's no point in checking contents anymore
                else:
                    return False

        if try_checking_contents:
            try:
                self._check_contents()
            except FilesCheckFailed:
                return False

        return True


def _with_deleted_suffix(p: Path) -> Path:
    return Path(str(p) + '.deleted')


@lru_cache(1)
def _input_hashes_log_enabled() -> bool:
    return bool(config.get_key("debug.input_hashes", default=False))
