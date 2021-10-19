from abc import ABC
from pathlib import Path
from dataclasses import fields, is_dataclass

from typing import Optional, List, Any, get_args, get_origin

from tasdmc import fileio, progress
from ..exceptions import FilesCheckFailed
from ..utils import file_contents_hash, concatenate_and_hash


class Files(ABC):
    """Abstract class for storing info on any set of files serving as inputs/outputs of tasdmc steps.

    Subclassed by each step to incapsulate specific behavior and checks.
    """

    @property
    def must_exist(self) -> List[Path]:
        """List of file Paths that must exist for Files to be valid step output. May be overriden by subclasses."""
        return []

    def prepare_for_step_run(self):
        """Ensure that Files are ready to be created from scratch in a step.run(). For example, delete existing
        files if they can't be automatically overwritten during step run.
        
        May be overriden by subclasses.
        """
        pass

    # methods for file checks

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
        """Returns bool value indicating if Files' were already produced.
        
        This is not the same as assert_files_are_ready as it also checks for files that may have been deleted
        because they are listed in not_retained.
        """
        try_checking_contents = True
        for f in self.must_exist:
            if not f.exists():
                if f in self.not_retained:  # maybe it was deleted? check if .deleted file exists
                    try_checking_contents = False  # but there's no point in checking contents anymore
                    if not Path(str(f) + '.deleted').exists():
                        return False
                else:
                    return False

        if try_checking_contents:
            try:
                self._check_contents()
            except FilesCheckFailed:            
                return False
        
        return True

    def _check_contents(self):
        """Check Files' content, should be overriden by subclasses. Must raise FilesCheckFailed on errors."""
        pass

    # methods for calculating Files' hash and storing it on disk for later check

    @property
    def to_be_hashed(self) -> Optional[List[Path]]:
        """Explicit list of file Paths that should be used to get Files' hash.
        
        If not overriden by a subclass and subclass is a dataclass, all Path and List[Path] fields are used.
        """
        return None

    @property
    def _to_be_hashed_paths(self) -> List[Path]:
        if self.to_be_hashed is not None:
            return self.to_be_hashed
        if not is_dataclass(self):
            raise TypeError(f"Cannot calculate stored Files' hash path with default method for non-dataclass")
        all_file_paths: List[Path] = []

        def is_list_of_paths(t: Any):
            args = get_args(t)
            return get_origin(t) is List and len(args) == 1 and args[0] == Path

        for f in fields(self):
            value = self.__getattribute__(f.name)
            if f.type == Path or f.type == 'Path':
                all_file_paths.append(value)
            elif is_list_of_paths(f.type) or f.type == 'List[Path]':
                all_file_paths.extend(value)
        return all_file_paths

    @property
    def _stored_hash_path(self) -> Path:
        """Hash is stored in a file with class name and file paths' (not content!) hash"""
        paths_id = concatenate_and_hash(self._to_be_hashed_paths)
        return fileio.input_hashes_dir() / f"{self.__class__.__name__}.{paths_id}"

    def _get_file_contents_hash(self, file: Path) -> str:
        if not file.exists():
            raise ValueError(
                f"Can't compute {self.__class__.__name__}'s contents hash, "
                + "some files to be hashed do not exist"
            )
        return file_contents_hash(file, hasher_name='md5')

    @property
    def contents_hash(self) -> str:
        file_hashes = []
        for file in self._to_be_hashed_paths:
            file_hashes.append(self._get_file_contents_hash(file))
        return concatenate_and_hash(file_hashes)

    def store_contents_hash(self):
        contents_hash = self.contents_hash
        with open(self._stored_hash_path, 'w') as f:
            f.write(contents_hash)

    def same_hash_as_stored(self) -> bool:
        stored_hash_path = self._stored_hash_path
        if not stored_hash_path.exists():
            return False
        with open(self._stored_hash_path, 'r') as f:
            stored_hash = f.read()
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
        progress.debug(f"Deleting not retained files for {self.__class__.__name__}")
        for f in self.not_retained:
            if f.exists():                
                with open(_with_deleted_suffix(f), 'w') as del_f:
                    del_f.write(
                        f'This file indicates that\n\n{f}\n\n'
                        + 'was produced and then deleted, its hash was\n\n'
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
                        raise ValueError(
                            f"Can't recover {self.__class__.__name__}'s contents hash from .deleted file"
                        )
            else:
                raise ValueError(
                    f"Can't compute {self.__class__.__name__}'s contents hash, "
                    + "some files to be hashed do not exist"
                )
        return file_contents_hash(file, hasher_name='md5')


def _with_deleted_suffix(p: Path) -> Path:
    return Path(str(p) + '.deleted')
