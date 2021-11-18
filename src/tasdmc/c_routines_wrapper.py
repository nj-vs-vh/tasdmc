import subprocess
from pathlib import Path
from dataclasses import dataclass

from typing import TextIO, Optional, List, Any

from tasdmc import config


def execute_routine(
    executable_name: str,
    args: List[Any],
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    global_: bool = False,  # i.e. executable dir is added to $PATH
    check_errors: bool = True,
):
    executable_path = str(config.Global.bin_dir / executable_name) if not global_ else executable_name
    return subprocess.run(
        [executable_path, *[str(a) for a in args]],
        stdout=stdout,
        stderr=stderr,
        capture_output=(stderr is None and stdout is None),
        check=check_errors,
    )


@dataclass
class Pipes:
    stdout_file: Path
    stderr_file: Optional[Path] = None
    append: bool = False

    def __post_init__(self):
        if self.stderr_file is None:
            self.stderr_file = self.stdout_file

    def __enter__(self):
        if not self.append:
            self.stdout_file.unlink(missing_ok=True)
            self.stderr_file.unlink(missing_ok=True)
        self.stdout = self.stdout_file.open('a')
        self.stderr = self.stderr_file.open('a')
        return (self.stdout, self.stderr)

    def __exit__(self, *args):
        self.stdout.close()
        self.stderr.close()


def concatenate_dst_files(source_files: List[Path], output_file: Path, stdout_file: Path, stderr_file: Path):
    with Pipes(stdout_file, stderr_file) as (stdout, stderr):
        execute_routine('dstcat.run', ['-o', output_file, *source_files], stdout, stderr, global_=True)


def list_events_in_dst_file(file: Path) -> List[str]:
    res = execute_routine('dstlist.run', [file], global_=True)
    return res.stdout.decode('utf-8').splitlines()
