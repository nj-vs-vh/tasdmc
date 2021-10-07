from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


class BadCorsikaOutputException(Exception):
    pass


@dataclass
class CorsikaOutputFiles:
    particle: Path
    longtitude: Path
    stdout: Path
    stderr: Path

    @classmethod
    def from_input_file(cls, input_file: Path, output_files_dir: Path) -> CorsikaOutputFiles:
        particle_file = output_files_dir / input_file.stem  # /path/to/corsika/output/DATnnnnnn
        return cls(
            particle_file,
            particle_file.with_suffix('.long'),
            particle_file.with_suffix('.stdout'),
            particle_file.with_suffix('.stderr'),
        )

    def splitted_particle_files(self, n: int):
        return [self.particle.with_suffix(f'.p{i:02d}') for i in range(n)]

    def check(self, raise_error: bool = True) -> bool:
        try:
            if not (
                self.particle.exists() and self.longtitude.exists() and self.stdout.exists and self.stderr.exists()
            ):
                raise BadCorsikaOutputException('One or more output files (particle, long, stderr, stdout) are missing')

            with open(self.stderr, 'r') as f:
                ignored_errmsg = 'Note: The following floating-point exceptions are signalling'
                error_messages = [line for line in f if not line.startswith(ignored_errmsg)]
                if len(error_messages) > 0:
                    raise BadCorsikaOutputException(
                        "CORSIKA stderr contains errors:\n" + '\n'.join([f'\t{line}' for line in error_messages])
                    )

            MIN_CORSIKA_LONG_FILE_LINE_COUNT = 1500
            with open(self.longtitude, 'r') as f:
                line_count = len([line for line in f])
                if line_count < MIN_CORSIKA_LONG_FILE_LINE_COUNT:
                    raise BadCorsikaOutputException(
                        "CORSIKA longtitude output file seems too short! "
                        + f"Only {line_count} lines with {MIN_CORSIKA_LONG_FILE_LINE_COUNT} expected"
                    )
        except BadCorsikaOutputException as e:
            if raise_error:
                raise e
            else:
                return False
        return True
