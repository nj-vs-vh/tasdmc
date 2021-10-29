import os
import subprocess
import resource
from pathlib import Path
from functools import lru_cache

from typing import TextIO, Optional, List, Any

from tasdmc import config, fileio


def _execute_cmd(
    executable_name: str,
    args: List[Any],
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
    global_excutable: bool = False,  # i.e. executable dir is added to $PATH
    check_errors: bool = True,
):
    executable_path = str(config.Global.bin_dir / executable_name) if not global_excutable else executable_name
    return subprocess.run(
        [executable_path, *[str(a) for a in args]],
        stdout=stdout,
        stderr=stderr,
        capture_output=(stderr is None and stdout is None),
        check=check_errors,
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


@lru_cache(1)
def _get_sdmc_spctr_executable():
    # looking for sdmc_spctr executable as it may be compiled with different suffixes
    sdmc_spctr_candidates: List[Path] = []
    PATH = os.environ['PATH']
    for executables_dir in PATH.split(':'):
        executables_dir = executables_dir.strip()
        if not executables_dir:
            continue
        for executable_file in Path(executables_dir).iterdir():
            if executable_file.name.startswith('sdmc_spctr'):
                sdmc_spctr_candidates.append(executable_file)

    if not sdmc_spctr_candidates:
        raise FileNotFoundError(f"sdmc_spctr_*.run not found on $PATH!")
    elif len(sdmc_spctr_candidates) > 1:
        requested_sdmc_spctr_name = config.get_key("throwing.sdmc_spctr_executable_name", default=None)
        if requested_sdmc_spctr_name is None:
            raise FileNotFoundError(
                "Multiple sdmc_spctr_*.run executables found on $PATH!:\n"
                + '\n'.join([f"\t{exe}" for exe in sdmc_spctr_candidates])
                + "\nSpecify throwing.sdmc_spctr_executable_name in run config"
            )
        else:
            sdmc_spctr_candidates = [ef for ef in sdmc_spctr_candidates if ef.name == requested_sdmc_spctr_name]
            if not sdmc_spctr_candidates:
                raise FileNotFoundError(f"Requested {requested_sdmc_spctr_name} executable not found on $PATH")
            elif len(sdmc_spctr_candidates) > 1:
                raise FileNotFoundError(
                    f"Found multiple executables matching requested {requested_sdmc_spctr_name}:\n"
                    + '\n'.join([f"\t{exe}" for exe in sdmc_spctr_candidates])
                    + '\nRemove some of them from $PATH to eliminate conflict'
                )
    return sdmc_spctr_candidates[0]  # we've ensured that this is the only option left!


def set_limits_for_sdmc_spctr():
    """equivalent to ulimit -s unlimited on command line"""
    _, hard_stack_limit = resource.getrlimit(resource.RLIMIT_STACK)
    resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, hard_stack_limit))


def test_sdmc_spctr_runnable():
    sdmc_spctr = _get_sdmc_spctr_executable()
    res = _execute_cmd(sdmc_spctr, [], global_excutable=True, check_errors=False)
    if not 'Usage: ' in res.stderr.decode('utf-8'):
        raise OSError(f'{sdmc_spctr} do not work as expected!')


def run_sdmc_spctr(
    tile: Path,
    output_event: Path,
    n_particles: int,
    random_seed: int,
    epoch: int,
    calibration_file: Path,
    smear_energies: bool,
    stdout_file: Path,
    stderr_file: Path,
) -> bool:
    """sdmc_spctr help:

    Usage: sdmc_spctr_2g_gcc_x86.run [1] [2] [3] [4]
    [1]: <str> DAT????XX_gea.dat sower library file (last 2 digits XX are the energy channel:
        XX=00-25: energy from 10^18.0 to 10^20.5 eV
        XX=26-39: energy from 10^16.6 to 10^17.9 eV
        XX=80-85: energy from 10^16.0 to 10^16.5 eV
    [2]: output DST file
    [3]: <float> Number of events (Poisson mean) to generate
    [4]: <int> Random seed number
    [5]: <int> Data set number (for sdcalib_[data set number].bin file,
    [6]: <str> Calibration file (/full/path/to/sdcalib_[data set number].bin file
        this number is the TA Date ("Epoch") calculated by TADay2Date function
    [7]: <str> Binary file with atmospheric muon data (/full/path/to/atmos.bin)
    [8]: <int> (OPT) Smear energies in 0.1 log10 bin according to E^-2? 1=YES,0-NO; default: 1
    [9]: <str> (OPT) Provide an ASCII file with azimuthal angles to use
                    1 column ASCII file, each line is azimuthal angle in degrees
                    CCW from East, along the shower propagation direction
                    By default, azimuthal angles are sampled randomly
    """

    try:
        with open(stdout_file, 'a') as stdout, open(stderr_file, 'a') as stderr:
            _execute_cmd(
                _get_sdmc_spctr_executable(),
                [
                    tile,
                    output_event,
                    n_particles,
                    random_seed,
                    epoch,
                    calibration_file,
                    fileio.DataFiles.atmos,
                    1 if smear_energies else 0,
                ],
                stdout=stdout,
                stderr=stderr,
                global_excutable=True,
            )
        return True
    except subprocess.CalledProcessError:
        return False
