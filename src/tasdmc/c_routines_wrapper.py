import subprocess
from pathlib import Path

from typing import TextIO, Optional, List, Any

from tasdmc import config, fileio


def _execute_cmd(executable_name: str, args: List[Any], stdout: Optional[TextIO] = None, stderr: Optional[TextIO] = None):
    subprocess.run(
        [config.Global.bin_dir / executable_name, *[str(a) for a in args]],
        stdout=stdout,
        stderr=stderr,
        capture_output=(stderr is None and stdout is None),
    )


def split_thinned_corsika_output(particle_file: Path, n_split: int, **execute_cmd_kwargs):
    _execute_cmd('corsika_split_th.run', [particle_file, n_split], **execute_cmd_kwargs)


def run_dethinning(particle_file: Path, output_file: Path, **execute_cmd_kwargs):
    _execute_cmd('dethinning.run', [particle_file, output_file], **execute_cmd_kwargs)


def run_corsika2geant(particle_files_listing: Path, output_file: Path, **execute_cmd_kwargs):
    _execute_cmd('corsika2geant.run', [particle_files_listing, fileio.DataFiles.sdgeant, output_file], **execute_cmd_kwargs)
