"""File input-output for all routines in the package"""

import os
import click
from pathlib import Path
import shutil
from functools import lru_cache

from tasdmc import config


config.Global.runs_dir.mkdir(exist_ok=True, parents=True)


def run_dir() -> Path:
    run_dir_name: str = config.get_key('name')
    return config.Global.runs_dir / run_dir_name


internal_dir_getters = []


def internal(fn):
    """Decorator to register internal dir so that it will be created when preparing run dir"""
    internal_dir_getters.append(fn)
    return lru_cache(maxsize=1)(fn)


@internal
def configs_dir() -> Path:
    return run_dir() / 'configs'


@internal
def corsika_input_files_dir() -> Path:
    return run_dir() / 'corsika_input'


@internal
def corsika_output_files_dir() -> Path:
    return run_dir() / 'corsika_output'


@internal
def dethinning_output_files_dir() -> Path:
    return run_dir() / 'corsika_output_dethinned'


def prepare_run_dir():
    rd = run_dir()
    if_exists = config.get_key('if_exists', default='error')
    if if_exists == 'continue':
        if rd.exists():
            click.secho(f"Run directory already exists, trying to continue operation", fg='red', bold=True)
        else:
            rd.mkdir()
    elif if_exists == 'overwrite':
        try:
            shutil.rmtree(rd)
        except FileNotFoundError:
            click.secho(f"Run directory existed and was overwritten", fg='red', bold=True)
        rd.mkdir()
    elif if_exists == 'error':
        try:
            rd.mkdir()
        except FileExistsError:
            raise ValueError(f"Run directory '{rd.name}' already exists, pick another run name")
    else:
        raise ValueError(
            f"if_exists config key must be 'continue', 'overwrite', or 'error', but {if_exists} was specified"
        )

    for idir_getter in internal_dir_getters:
        idir_getter().mkdir(exist_ok=config.try_to_continue())

    config.dump(configs_dir() / 'run.yaml')
