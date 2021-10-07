"""Running CORSIKA, dethinning and GEANT simulations on prepared input files"""

from __future__ import annotations
import corsika_wrapper as cw
from tqdm import tqdm
import click
from pathlib import Path
from typing import Dict

from ..fileio import corsika_input_files_dir, corsika_output_files_dir
from ..config import get_config_key, get_try_to_continue, get_verbosity

from .output_files import CorsikaOutputFiles, CorsikaSplitOutputFiles
from .dethinning import split_thinned_corsika_output


def run_simulation(config):
    verbose = get_verbosity(config) > 0
    if verbose:
        click.secho("\nRunning simulation\n", bold=True)

    infiles_dir = corsika_input_files_dir(config)
    outfiles_dir = corsika_output_files_dir(config)
    try_to_continue = get_try_to_continue(config)
    corsika_kwargs = {  # common kwargs for corsika_wrapper
        'corsika_path': get_config_key(config, 'corsika.path'),
        'save_stdout': True,
    }
    particle_file_split_to = get_config_key(config, 'dethinning.particle_file_split_to')

    corsika_infiles = [f for f in infiles_dir.iterdir()]
    if verbose:
        corsika_infiles = tqdm(corsika_infiles)  # TODO: find solution for multiprocessing progress bar

    for infile in corsika_infiles:
        # NOTE: multiprocessing parallelism will be done here with ProcessPoolExecutor
        run_simulation_on_file(
            corsika_input_file=infile,
            corsika_output_files_dir=outfiles_dir,
            try_to_continue=try_to_continue,
            corsika_kwargs=corsika_kwargs,
            particle_file_split_to=particle_file_split_to,
        )


def run_simulation_on_file(
    corsika_input_file: Path,
    corsika_output_files_dir: Path,
    try_to_continue: bool,
    corsika_kwargs: Dict,
    particle_file_split_to: int,
):
    cof = CorsikaOutputFiles.from_input_file(corsika_input_file, corsika_output_files_dir)
    if not (try_to_continue and cof.check(raise_error=False)):
        cof.clear()
        cw.corsika(
            steering_card=cw.read_steering_card(corsika_input_file),
            output_path=str(
                corsika_output_files_dir / corsika_input_file.stem
            ),  # stdout and stderr suffixes are appended by corsika_wrapper
            **corsika_kwargs,
        )
        cof.check()

    csof = CorsikaSplitOutputFiles.from_corsika_output(cof, n_split=particle_file_split_to)
    if not (try_to_continue and csof.check(raise_error=False)):
        csof.clear()
        split_thinned_corsika_output(cof.particle, particle_file_split_to)
        csof.check()
