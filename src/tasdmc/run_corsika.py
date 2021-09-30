"""Running CORSIKA simulations on prepared input files, thread safe thanks to corsika_wrapper module"""

import corsika_wrapper as cw
from tqdm import tqdm
import click

from .fileio import corsika_input_files_dir, corsika_output_files_dir
from .config import get_config_key, get_verbosity


def run_corsika(config):
    verbose = get_verbosity(config) > 0
    if verbose:
        click.secho("\nRunning CORSIKA\n", bold=True)

    infiles_dir = corsika_input_files_dir(config)
    outfiles_dir = corsika_output_files_dir(config)
    outfiles_dir.mkdir()

    corsika_infiles = [f for f in infiles_dir.iterdir()]
    if verbose:
        corsika_infiles = tqdm(corsika_infiles)
    for infile in corsika_infiles:
        outfile = outfiles_dir / (infile.stem + '.evtio')
        cw.corsika(
            corsika_path=get_config_key(config, 'corsika.path'),
            steering_card=cw.read_steering_card(infile), 
            output_path=str(outfile),
            save_stdout=True,
        )
