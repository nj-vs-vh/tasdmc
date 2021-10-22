"""File input-output for all routines in the package"""

import os
import click
import shutil
from pathlib import Path
from functools import lru_cache
from datetime import datetime

from typing import Optional

from tasdmc import config


class DataFiles:
    sdgeant = config.Global.data_dir / 'sdgeant.dst'


config.Global.runs_dir.mkdir(exist_ok=True, parents=True)


def run_dir(run_name: Optional[str] = None) -> Path:
    run_name: str = run_name or config.get_key('name')
    return config.Global.runs_dir / run_name


_internal_dir_getters = []


def internal_dir(fn):
    """Decorator to register internal dir so that it will be created when preparing run dir"""
    _internal_dir_getters.append(fn)
    return lru_cache()(fn)


@internal_dir
def configs_dir(run_name: Optional[str] = None) -> Path:
    return run_dir(run_name) / 'configs'


@internal_dir
def corsika_input_files_dir() -> Path:
    return run_dir() / 'corsika_input'


@internal_dir
def corsika_output_files_dir() -> Path:
    return run_dir() / 'corsika_output'


@internal_dir
def dethinning_output_files_dir() -> Path:
    return run_dir() / 'corsika_output_dethinned'


@internal_dir
def c2g_output_files_dir() -> Path:
    return run_dir() / 'corsika2geant_output'


@internal_dir
def input_hashes_dir() -> Path:
    return run_dir() / '_input_files_hashes'


@internal_dir
def logs_dir() -> Path:
    return run_dir() / 'logs'


@internal_dir
def pipeline_logs_dir() -> Path:
    return logs_dir() / 'pipeline'


# individual files


def saved_main_process_id_file():
    return run_dir() / 'main_process_id.txt'


def saved_run_config_file(run_name: Optional[str] = None):
    return configs_dir(run_name) / 'run.yaml'


def multiprocessing_debug_log():
    return logs_dir() / 'multiprocessing_debug.log'


def cards_gen_info_log():
    return logs_dir() / 'cards_generation_info.log'


def pipeline_log(pipeline_id: str):
    return pipeline_logs_dir() / f'{pipeline_id}.yaml'


def pipeline_failed_file(pipeline_id: str):
    return pipeline_logs_dir() / f'{pipeline_id}.failed'


# top-level functions


def prepare_run_dir():
    rd = run_dir()
    if config.try_to_continue():
        if rd.exists():
            click.secho(f"Run already exists, continuing", fg='red', bold=True)
        else:
            rd.mkdir()
    else:
        try:
            rd.mkdir()
        except FileExistsError:
            raise ValueError(f"Run '{rd.name}' already exists, pick another run name or set continue: True in config")

    if logs_dir().exists():
        old_logs_dir_name = f'before-{datetime.utcnow().isoformat(timespec="seconds")}'
        old_logs_dir = logs_dir() / old_logs_dir_name
        old_logs_dir.mkdir()
        for old_log in logs_dir().glob('*'):
            if not old_log.name.startswith('before'):
                shutil.move(old_log, old_logs_dir / old_log.name)

    for idir_getter in _internal_dir_getters:
        idir_getter().mkdir(exist_ok=config.try_to_continue())

    config.dump(saved_run_config_file())
    saved_main_process_id_file().write_text(str(os.getpid()))  # saving currend main process ID


def get_saved_main_process_id():
    return int(saved_main_process_id_file().read_text())


def get_run_config_path(run_name: str) -> Path:
    if not run_dir(run_name).exists():
        raise ValueError(f"Run '{run_name}' not found")
    return saved_run_config_file(run_name)
