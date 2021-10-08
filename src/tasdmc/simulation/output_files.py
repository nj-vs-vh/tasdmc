from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from pathlib import Path

from typing import Dict, List


class BadOutputFilesException(Exception):
    pass


class OutputFiles(ABC):
    @property
    @abstractmethod
    def all_files(self) -> List[Path]:
        pass

    def clear(self):
        for f in self.all_files:
            f.unlink(missing_ok=True)

    @abstractmethod
    def _check():
        """raise BadOutputFilesException if comething's wrong"""
        pass

    def check(self, raise_error: bool = True) -> bool:
        try:
            self._check()
        except BadOutputFilesException as e:
            if raise_error:
                raise e
            else:
                return False
        return True


@dataclass
class CorsikaOutputFiles(OutputFiles):
    particle: Path
    longtitude: Path
    stdout: Path
    stderr: Path

    @property
    def all_files(self) -> List[Path]:
        return [self.particle, self.longtitude, self.stderr, self.stdout]

    @classmethod
    def from_input_file(cls, input_file: Path, output_files_dir: Path) -> CorsikaOutputFiles:
        particle_file = output_files_dir / input_file.stem  # /path/to/corsika/output/DATnnnnnn
        return cls(
            particle_file,
            particle_file.with_suffix('.long'),
            particle_file.with_suffix('.stdout'),
            particle_file.with_suffix('.stderr'),
        )

    def _check(self):
        if not all([f.exists() for f in self.all_files]):
            raise BadOutputFilesException('One or more output files (particle, long, stderr, stdout) are missing')

        with open(self.stderr, 'r') as spf:
            ignored_errmsg = 'Note: The following floating-point exceptions are signalling'
            error_messages = [line for line in spf if not line.startswith(ignored_errmsg)]
            if len(error_messages) > 0:
                raise BadOutputFilesException(
                    f"{self.stderr.name} contains errors:\n" + '\n'.join([f'\t{line}' for line in error_messages])
                )

        MIN_CORSIKA_LONG_FILE_LINE_COUNT = 1500
        with open(self.longtitude, 'r') as spf:
            line_count = len([line for line in spf])
            if line_count < MIN_CORSIKA_LONG_FILE_LINE_COUNT:
                raise BadOutputFilesException(
                    f"{self.longtitude.name} seems too short! "
                    + f"Only {line_count} lines, but {MIN_CORSIKA_LONG_FILE_LINE_COUNT} expected."
                )

        with open(self.stdout, 'r') as spf:
            for line in spf:
                pass
            if not (isinstance(line, str) and 'END OF RUN' in line):
                raise BadOutputFilesException(f"{self.stdout.name} does not end with END OF RUN.")

        _check_particle_file(self.particle)


@dataclass
class CorsikaSplitOutputFiles(OutputFiles):
    splitted_particle: List[Path]

    @property
    def all_files(self) -> List[Path]:
        return self.splitted_particle

    @classmethod
    def from_corsika_output(cls, cof: CorsikaOutputFiles, n_split: int) -> CorsikaSplitOutputFiles:
        return cls([cof.particle.with_suffix(f'.p{i+1:02d}') for i in range(n_split)])

    def _check(self):
        for spf in self.splitted_particle:
            if not spf.exists():
                raise BadOutputFilesException(f"Splitted particle file {spf.name} (and maybe others) do not exist")
            _check_particle_file(spf)


@dataclass
class DethinningOutputFiles(OutputFiles):
    particle_to_dethinned: Dict[Path, Path]

    @property
    def all_files(self) -> List[Path]:
        return list(self.particle_to_dethinned.values())

    @classmethod
    def from_corsika_split_output(cls, csof: CorsikaSplitOutputFiles) -> DethinningOutputFiles:
        return cls({f: f.with_suffix(f.suffix + '.dethinned') for f in csof.splitted_particle})

    def _check(self):
        for dethinned_file in self.all_files:
            if not dethinned_file.exists():
                raise BadOutputFilesException(
                    f"Dethinned particle file {dethinned_file.name} (and maybe others) do not exist"
                )


def _check_particle_file(particle_file: Path):
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
    raise BadOutputFilesException(f"{particle_file.name} doesn't contain RUNE at the end")
