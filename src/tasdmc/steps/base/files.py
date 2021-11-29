from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import fields, is_dataclass
from functools import lru_cache

from typing import Optional, List, Any, Literal, get_args, get_origin

from tasdmc import fileio, config
from tasdmc.logs import input_hashes_debug, file_checks_debug
from tasdmc.utils import concatenate_and_hash
from ..exceptions import FilesCheckFailed, HashComputationFailed
from ..utils import file_contents_hash


class Files(ABC):
    """Abstract class for storing info on any set of files serving as inputs/outputs of tasdmc steps.

    Subclassed by each step to incapsulate specific behavior and checks.
    """

    @property
    @abstractmethod
    def must_exist(self) -> List[Path]:
        """List of file Paths that must exist for Files to be a valid step output. Must be overriden by subclasses."""
        pass

    def __new__(cls, *args, **kwargs):
        if not is_dataclass(cls):
            raise TypeError("All Files subclasses must be dataclasses!")
        return super(Files, cls).__new__(cls)

    def __str__(self):
        return self.id_

    @property
    def all_files(self) -> List[Path]:
        """All file paths in Files'. Since all subclasses are dataclasses, this can be inferred
        from Path-typed fields automatically.

        May be overriden by subclasses.
        """
        def is_list_of_paths(t: Any):
            args = get_args(t)
            origin = get_origin(t)
            return origin in {List, list} and len(args) == 1 and args[0] == Path

        all_file_paths: List[Path] = []
        for f in fields(self):
            value = self.__getattribute__(f.name)
            if f.type == Path or f.type == 'Path':
                all_file_paths.append(value)
            elif is_list_of_paths(f.type) or f.type == 'List[Path]':
                all_file_paths.extend(value)
        return all_file_paths

    def clean(self):
        for f in self.all_files:
            f.unlink(missing_ok=True)

    def total_size(self, units: Literal['b', 'Kb', 'Mb', 'Gb']) -> int:
        """Total Files' size in specified units"""
        size_by_unit = {
            'b': 1,
            'Kb': 1024,
            'Mb': 1024 ** 2,
            'Gb': 1024 ** 3,
        }
        return sum([f.stat().st_size / size_by_unit[units] for f in self.all_files if f.exists()])

    def prepare_for_step_run(self):
        """Ensure that Files are ready to be created from scratch in a step.run(). For example, delete existing
        files if they can't be automatically overwritten during step run.

        May be overriden by subclasses.
        """
        pass

    # Files' validation methods

    def assert_files_are_ready(self):
        """Check Files if they are ready and raise FilesCheckFailes exception if there's a problem.

        Should not be overriden, but modified indirectly by overriding must_exist property and _check_contents method.
        """
        nonexistent_files: List[Path] = []
        for f in self.must_exist:
            if not f.exists():
                nonexistent_files.append(f)
        if nonexistent_files:
            raise FilesCheckFailed(
                "Following required files do not exist: \n"
                + "\n".join([f"\t{missing_file.relative_to(fileio.run_dir())}" for missing_file in nonexistent_files])
            )
        else:
            self._check_contents()

    def files_were_produced(self) -> bool:
        """Returns bool value indicating if Files' were already produced.
        
        This differs from assert_files_are_ready in semantics: files were once produced (i.e. the step producing it was
        completed) vs files are ready at the moment (i.e. ready to be consumed by a step as input). See subclasses for
        details.
        """
        try:
            self.assert_files_are_ready()
            return True
        except FilesCheckFailed as e:
            if _file_checks_log_enabled():
                file_checks_debug(f"{self} check failed:\n{e}")
            return False

    def _check_contents(self):
        """Check Files' contents in a specific way (e.g. checking for errors in stderr file, validating binary files).
        Must raise FilesCheckFailed on errors.

        Should be overriden by subclasses."""
        pass

    # methods for calculating Files' hash and storing it on disk for later check

    @property
    def id_paths(self) -> Optional[List[Path]]:
        """Explicit list of file paths that uniquely identify the Files instance

        If not overriden by a subclass and subclass is a dataclass, all Path and List[Path] fields are used.
        """
        return None

    @property
    def _id_paths(self) -> List[Path]:
        if self.id_paths is not None:
            return self.id_paths
        else:
            return self.all_files

    @property
    def id_(self) -> str:
        """Unique identitifer for Files instance"""
        paths_id = concatenate_and_hash(self._id_paths)
        return f"{self.__class__.__name__}.{paths_id}"

    @property
    def _stored_hash_path(self) -> Path:
        return fileio.input_hashes_dir() / self.id_

    def _get_file_contents_hash(self, file: Path) -> str:
        if not file.exists():
            raise HashComputationFailed(
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
        for file in self._id_paths:
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
                input_hashes_debug(f"{self} has no stored hash, comparison FAILED")
            return False
        with open(stored_hash_path, 'r') as f:
            stored_hash = f.read()
        if _input_hashes_log_enabled() and self.contents_hash != stored_hash:
            input_hashes_debug(
                f"{self} hash comparison "
                + f"FAILED (actual hash: {self.contents_hash}; stored hash: {stored_hash})"
            )
        return self.contents_hash == stored_hash


class _AllowedToBeMissingFiles(Files):
    """Files assume that all files in must_exist must actually exist but this may not be the case"""

    @abstractmethod
    def _get_missing_file_contents_hash(self, file: Path) -> str:
        pass

    def _get_file_contents_hash(self, file: Path) -> str:
        if not file.exists():
            return self._get_missing_file_contents_hash(file)
        else:
            return super()._get_file_contents_hash(file)

    @abstractmethod
    def _files_were_produced_but_some_missing(self) -> bool:
        pass

    def files_were_produced(self) -> bool:
        for f in self.must_exist:
            if not f.exists():
                return self._files_were_produced_but_some_missing()
        return super().files_were_produced()


class NotAllRetainedFiles(_AllowedToBeMissingFiles):
    """Subclass for cases when some of the files are not retained (e.g., they are too big or just redundant)
    
    In this case the "original" file will be deleted and "original.deleted" will be created in its place,
    containing info about "original"'s size and contents hash.
    """

    @property
    @abstractmethod
    def not_retained(self) -> List[Path]:
        """List of file Paths that can be removed after they have been used in pipeline. This should include
        temporary or very large files, unnecessary for the end result. May be overriden by subclasses.
        """
        pass

    def __post_init__(self):
        if not set(self.not_retained).issubset(self.must_exist):
            raise ValueError(f"All not retained files must also be marked as must_exist")

    def _get_missing_file_contents_hash(self, file: Path) -> str:
        deleted_file = self._with_deleted_suffix(file)
        if deleted_file.exists():
            with open(deleted_file, 'r') as df:
                last_line = ''
                for line in df:
                    if line.strip():
                        last_line = line
                if len(last_line) == 32:
                    return last_line
                else:
                    raise HashComputationFailed(
                        f"Can't recover {self.__class__.__name__}'s contents hash from {deleted_file}"
                    )
        else:
            raise HashComputationFailed(
                f"Can't compute {self.__class__.__name__}'s contents hash, "
                + "some files to be hashed and their .deleted traces do not exist"
            )

    def _files_were_produced_but_some_missing(self) -> bool:
        for f in self.must_exist:
            if not f.exists():
                if f not in self.not_retained or not self._with_deleted_suffix(f).exists():
                    if _file_checks_log_enabled():
                        if f not in self.not_retained:
                            file_checks_debug(
                                f"{self} check failed:\n"
                                + f"{f.name} is missing and isn't marked as not retained"
                            )
                        elif not self._with_deleted_suffix(f).exists():
                            file_checks_debug(
                                f"{self} check failed:\n"
                                + f"both {f.name} and {self._with_deleted_suffix(f).name} are missing"
                            )
                    return False
        return True

    def clean(self):
        for f in self.all_files:
            f.unlink(missing_ok=True)
            self._with_deleted_suffix(f).unlink(missing_ok=True)

    @staticmethod
    def _with_deleted_suffix(p: Path) -> Path:
        return Path(str(p) + '.deleted')

    def delete_not_retained_files(self):
        """Delete files that are not retained after pipeline end and create .deleted files in their place"""
        for f in self.not_retained:
            if f.exists():
                with open(self._with_deleted_suffix(f), 'w') as del_f:
                    del_f.write(
                        f'{f}\nwas produced bytes and then deleted\n\n'
                        + f'its size was {f.stat().st_size} bytes\n\n'
                        + 'its contents hash was:\n'
                        + file_contents_hash(f)
                    )
                f.unlink()


class OptionalFiles(Files):
    """Subclass for cases when Files may or may not be produced. If they are, they are checked as always."""

    @property
    @abstractmethod
    def optional(self) -> List[Path]:
        pass

    @property
    def id_paths(self) -> List[Path]:
        return [p for p in self.all_files if p not in self.optional]

    def __post_init__(self):
        if set(self.optional).intersection(self.must_exist):
            raise ValueError(f"All not retained files must also be marked as must_exist")

    @property
    def is_realized(self) -> bool:
        return all(f.exists() for f in self.optional)

    def _check_contents(self):
        self._check_mandatory_files_contents()
        if self.is_realized:
            self._check_optional_files_contents()

    def _check_mandatory_files_contents(self):
        pass

    def _check_optional_files_contents(self):
        """May be overriden in the same way as _check_contents for other Files"""
        pass            


@lru_cache(1)
def _input_hashes_log_enabled() -> bool:
    return bool(config.get_key("debug.input_hashes", default=False))


@lru_cache(1)
def _file_checks_log_enabled() -> bool:
    return bool(config.get_key("debug.file_checks", default=False))
