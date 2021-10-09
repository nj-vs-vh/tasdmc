"""Running CORSIKA, dethinning and GEANT simulations on prepared input files"""

from __future__ import annotations
import corsika_wrapper as cw
import click
from pathlib import Path

from tasdmc import fileio, config

from .output_files import CorsikaOutputFiles, CorsikaSplitOutputFiles, DethinningOutputFiles
from .dethinning import run_dethinning, split_thinned_corsika_output


def run_simulation():
    verbose = config.verbosity() > 0
    if verbose:
        click.secho("\nRunning simulation\n", bold=True)

    for infile in [f for f in fileio.corsika_input_files_dir().iterdir()]:
        # NOTE: multiprocessing parallelism will be done here with ProcessPoolExecutor
        run_simulation_on_file(infile)


def run_simulation_on_file(corsika_input_file: Path):
    verbose = config.verbosity() > 0
    if verbose:
        click.secho(f"Processing {corsika_input_file.name}...")

    cof = CorsikaOutputFiles.from_input_file(corsika_input_file, fileio.corsika_output_files_dir())
    if not (config.try_to_continue() and cof.check(raise_error=False)):
        click.secho('Running CORSIKA', dim=True)
        cof.clear()
        cw.corsika(
            steering_card=cw.read_steering_card(corsika_input_file),
            output_path=str(
                fileio.corsika_output_files_dir() / corsika_input_file.stem
            ),  # stdout and stderr suffixes are appended by corsika_wrapper
            corsika_path=config.get_key('corsika.path'),
            save_stdout=True,
        )
        cof.check()
    else:
        click.secho('CORSIKA output found, skipping', dim=True)

    n_split = config.get_key('dethinning.particle_file_split_to')
    csof = CorsikaSplitOutputFiles.from_corsika_output(cof, n_split=n_split)
    if not (config.try_to_continue() and csof.check(raise_error=False)):
        click.secho(f'Splitting CORSIKA output to {n_split} parts', dim=True)
        csof.clear()
        split_thinned_corsika_output(cof.particle, n_split)
        csof.check()
    else:
        click.secho(f'Splitted CORSIKA output found, skipping', dim=True)

    # TODO: check file existence on per-file basis, not in bulk!
    dof = DethinningOutputFiles.from_corsika_split_output(csof)
    if not (config.try_to_continue() and dof.check(raise_error=False)):
        click.secho(f'Running dethinning', dim=True)
        dof.clear()
        for particle, dethinned in dof.particle_to_dethinned.items():
            run_dethinning(particle, dethinned)
        dof.check()
    else:
        click.secho(f'Dethinning found, skipping', dim=True)
