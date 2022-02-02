import subprocess
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import resource

from typing import TextIO, Optional, List, Any

from tasdmc import config, fileio


@lru_cache(1)
def debug_routines_execution():
    return bool(config.get_key("debug.external_routine_commands", default=False))


def execute_routine(
    executable: str,
    args: List[Any],
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    global_: bool = False,  # i.e. executable dir is added to $PATH
    check_errors: bool = True,
    stdin_content: Optional[str] = None,
    run_from_directory: Optional[Path] = None,
):
    executable_path = str(config.Global.bin_dir / executable) if not global_ else executable

    routine_cmd = " ".join([str(a) for a in [executable_path, *args]])
    if debug_routines_execution():
        with open(fileio.routine_cmd_debug_log(), 'a') as f:
            f.write(routine_cmd + "\n")

    result = subprocess.run(
        [executable_path, *[str(a) for a in args]],
        cwd=run_from_directory,
        stdout=stdout,
        stderr=stderr,
        input=stdin_content,
        encoding="utf-8" if stdin_content is not None else None,
        capture_output=(stderr is None and stdout is None),
        check=check_errors,
    )

    if debug_routines_execution() and result.returncode != 0:
        with open(fileio.routine_cmd_debug_log(), 'a') as f:
            f.write(f"\nFAILED:\n{routine_cmd}\n\n")

    return result


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


class UnlimitedStackSize:
    """Equivalent to ulimit -s unlimited in a bash script"""

    def __enter__(self):
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        self.previous_stack_limits = (soft, hard)
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, hard))

    def __exit__(self, *args):
        resource.setrlimit(resource.RLIMIT_STACK, self.previous_stack_limits)
