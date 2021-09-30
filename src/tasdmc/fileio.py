"""File input-output for all the routines in the package"""

import os
import yaml
import click
from pathlib import Path
import shutil

from .config import Config, get_config_key


RUNS_DIR = os.environ.get("TASDMC_RUNS_DIR") or Path(os.getcwd()) / 'runs'
RUNS_DIR.mkdir(exist_ok=True)


def run_dir(config: Config) -> Path:
    run_dir_name: str = get_config_key(config, 'name')
    return RUNS_DIR / run_dir_name


def prepare_run_dir(config):
    verbose = get_config_key(config, 'verbosity') > 0
    if_exists = get_config_key(config, 'if_exists', default='error')
    if if_exists == 'append_index':
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
        shutil.rmtree(rd, ignore_errors=True)
        rd.mkdir()
    elif if_exists == 'error':
        rd = run_dir(config)
        try:
            rd.mkdir()
        except FileExistsError:
            raise ValueError(f"Run name '{rd.name}' taken")
    else:
        raise ValueError(f"if_exists config key must be 'overwrite', 'append_index', or 'error', but {if_exists} was passed")

    run_configs_dir = rd / 'configs'
    run_configs_dir.mkdir()

    with open(run_configs_dir / 'run.yaml', 'w') as f:
        yaml.dump(config, f)


def corsika_input_files_dir(config) -> Path:
    return run_dir(config) / 'infiles'


def corsika_output_files_dir(config) -> Path:
    return run_dir(config) / 'corsika_output'
