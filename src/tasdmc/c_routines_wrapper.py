import subprocess
from pathlib import Path

from typing import TextIO, Optional, List, Any

from tasdmc import config, fileio


def _execute_cmd(
    executable_name: str,
    args: List[Any],
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    global_excutable: bool = False,  # i.e. executable dir is added to $PATH
):
    executable_path = str(config.Global.bin_dir / executable_name) if not global_excutable else executable_name
    subprocess.run(
        [executable_path, *[str(a) for a in args]],
        stdout=stdout,
        stderr=stderr,
        capture_output=(stderr is None and stdout is None),
        check=True,
    )


def split_thinned_corsika_output(particle_file: Path, n_split: int):
    _execute_cmd('corsika_split_th.run', [particle_file, n_split])


def run_dethinning(particle_file: Path, output_file: Path, stdout_file: Path, stderr_file: Path):
    with open(stdout_file, 'w') as stdout, open(stderr_file, 'w') as stderr:
        _execute_cmd('dethinning.run', [particle_file, output_file], stdout, stderr)


def run_corsika2geant(particle_files_listing: Path, output_file: Path, stdout_file: Path, stderr_file: Path):
    with open(stdout_file, 'w') as stdout, open(stderr_file, 'w') as stderr:
        _execute_cmd(
            'corsika2geant.run',
            [particle_files_listing, fileio.DataFiles.sdgeant, output_file],
            stdout,
            stderr,
        )


def check_tile_file(tile_file: Path, stdout_file: Path, stderr_file: Path):
    with open(stdout_file, 'w') as stdout, open(stderr_file, 'w') as stderr:
        _execute_cmd(
            'check_gea_dat_file.run',
            [tile_file],
            stdout,
            stderr,
        )


def run_sdmc_calib_extract(
    constants_file: Path, output_file: Path, raw_calibration_files: List[Path], stdout_file: Path, stderr_file: Path
):
    with open(stdout_file, 'w') as stdout, open(stderr_file, 'w') as stderr:
        _execute_cmd(
            'sdmc_calib_extract.run',
            ['-c', constants_file, '-o', output_file, *raw_calibration_files],
            stdout,
            stderr,
            global_excutable=True,
        )
