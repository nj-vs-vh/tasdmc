"""File input-output for all the routines in the package"""

import os
import yaml
import click
from pathlib import Path
import shutil
from functools import wraps

from .config import Config, get_config_key


RUNS_DIR = Path(os.environ.get("TASDMC_RUNS_DIR")) or Path(os.getcwd()) / 'runs'
RUNS_DIR.mkdir(exist_ok=True)


def run_dir(config: Config) -> Path:
    run_dir_name: str = get_config_key(config, 'name')
    return RUNS_DIR / run_dir_name


def run_configs_dir(config: Config) -> Path:
    return run_dir(config) / 'configs'


def corsika_input_files_dir(config: Config) -> Path:
    return run_dir(config) / 'corsika_input'


def corsika_output_files_dir(config: Config) -> Path:
    return run_dir(config) / 'corsika_output'


def prepare_run_dir(config: Config):
    verbose = get_config_key(config, 'verbosity') > 0
    if_exists = get_config_key(config, 'if_exists', default='error')
    if if_exists == 'continue':
        if run_dir(config).exists():
            click.secho(f"Run directory already exists, trying to continue operation", fg='red', bold=True)
    elif if_exists == 'append_index':
        run_dir_idx = None
        run_dir_name_plain = run_dir(config).name
        while True:
            rd = run_dir(config)
            try:
                rd.mkdir()
                if run_dir_idx is not None and verbose:
                    click.secho(
                        f"Run name '{run_dir_name_plain}' taken, updated to '{rd.name}'",
                        fg='red',
                        bold=True,
                    )
                break
            except FileExistsError:
                run_dir_idx = run_dir_idx + 1 if run_dir_idx is not None else 1
                config['name'] = run_dir_name_plain + '-' + str(run_dir_idx)
    elif if_exists == 'overwrite':
        rd = run_dir(config)
        try:
            shutil.rmtree(rd)
        except FileNotFoundError:
            click.secho(f"Run directory existed and was overwritten", fg='red', bold=True)
        rd.mkdir()
    elif if_exists == 'error':
        rd = run_dir(config)
        try:
            rd.mkdir()
        except FileExistsError:
            raise ValueError(f"Run directory '{rd.name}' already exists, pick another run name")
    else:
        raise ValueError(
            "if_exists config key must be 'continue', 'overwrite', 'append_index', or 'error', "
            + f"but {if_exists} was specified"
        )

    for internal_dir in (run_configs_dir, corsika_input_files_dir, corsika_output_files_dir):
        internal_dir(config).mkdir(exist_ok=(if_exists == 'continue'))

    configs_dir = run_configs_dir(config)

    with open(configs_dir / 'run.yaml', 'w') as f:
        yaml.dump(config, f)
