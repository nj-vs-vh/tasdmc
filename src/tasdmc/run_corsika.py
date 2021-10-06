"""Running CORSIKA simulations on prepared input files, thread safe thanks to corsika_wrapper module"""

import corsika_wrapper as cw
from tqdm import tqdm
import click

from .fileio import corsika_input_files_dir, corsika_output_files_dir
from .config import get_config_key, get_try_to_continue, get_verbosity


def run_corsika(config):
    verbose = get_verbosity(config) > 0
    if verbose:
        click.secho("\nRunning CORSIKA\n", bold=True)
    try_to_continue = get_try_to_continue(config)

    infiles_dir = corsika_input_files_dir(config)
    outfiles_dir = corsika_output_files_dir(config)
    outfiles_dir.mkdir(exist_ok=try_to_continue)


    corsika_infiles = [f for f in infiles_dir.iterdir()]
    if verbose:
        corsika_infiles = tqdm(corsika_infiles)

    for infile in corsika_infiles:
        outfile = outfiles_dir / infile.stem

        particle_file = outfile
        longtitude_file = outfile.with_suffix('.long')
        stdout_file = outfile.with_suffix('.stdout')
        stderr_file = outfile.with_suffix('.stderr')

        if (
            try_to_continue
            and particle_file.exists()
            and longtitude_file.exists()
            and stdout_file.exists()
            and stderr_file.exists()
        ):
            continue
        else:
            cw.corsika(
                corsika_path=get_config_key(config, 'corsika.path'),
                steering_card=cw.read_steering_card(infile), 
                output_path=str(outfile),  # stdout and stderr suffixes are appended by corsika_wrapper
                save_stdout=True,
            )
