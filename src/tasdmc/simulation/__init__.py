"""Running CORSIKA, dethinning and GEANT simulations on prepared input files"""

from __future__ import annotations
import corsika_wrapper as cw
from tqdm import tqdm
import click
from pathlib import Path
from typing import Dict

from ..fileio import corsika_input_files_dir, corsika_output_files_dir
from ..config import get_config_key, get_try_to_continue, get_verbosity

from .output_files import CorsikaOutputFiles, CorsikaSplitOutputFiles, DethinningOutputFiles
from .dethinning import run_dethinning, split_thinned_corsika_output


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

    for infile in corsika_infiles:
        # NOTE: multiprocessing parallelism will be done here with ProcessPoolExecutor
        run_simulation_on_file(
            corsika_input_file=infile,
            corsika_output_files_dir=outfiles_dir,
            try_to_continue=try_to_continue,
            corsika_kwargs=corsika_kwargs,
            particle_file_split_to=particle_file_split_to,
            verbose=verbose,
        )


def run_simulation_on_file(
    corsika_input_file: Path,
    corsika_output_files_dir: Path,
    try_to_continue: bool,
    corsika_kwargs: Dict,
    particle_file_split_to: int,
    verbose: bool,
):
    if verbose:
        click.secho(f"Processing {corsika_input_file.name}...")

    cof = CorsikaOutputFiles.from_input_file(corsika_input_file, corsika_output_files_dir)
    if not (try_to_continue and cof.check(raise_error=False)):
        click.secho('Running CORSIKA', dim=True)
        cof.clear()
        cw.corsika(
            steering_card=cw.read_steering_card(corsika_input_file),
            output_path=str(
                corsika_output_files_dir / corsika_input_file.stem
            ),  # stdout and stderr suffixes are appended by corsika_wrapper
            **corsika_kwargs,
        )
        cof.check()
    else:
        click.secho('CORSIKA output found, skipping', dim=True)

    csof = CorsikaSplitOutputFiles.from_corsika_output(cof, n_split=particle_file_split_to)
    if not (try_to_continue and csof.check(raise_error=False)):
        click.secho(f'Splitting CORSIKA output to {particle_file_split_to} parts', dim=True)
        csof.clear()
        split_thinned_corsika_output(cof.particle, particle_file_split_to)
        csof.check()
    else:
        click.secho(f'Splitted CORSIKA output found, skipping', dim=True)

    # TODO: check file existence on per-file basis, not in bulk!
    dof = DethinningOutputFiles.from_corsika_split_output(csof)
    if not (try_to_continue and dof.check(raise_error=False)):
        click.secho(f'Running dethinning', dim=True)
        dof.clear()
        for particle, dethinned in dof.particle_to_dethinned.items():
            run_dethinning(particle, dethinned)
        dof.check()
    else:
        click.secho(f'Dethinning found, skipping', dim=True)
