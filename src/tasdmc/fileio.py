"""File input-output for all routines in the package"""

import os
import shutil
from pathlib import Path
from functools import lru_cache
from datetime import datetime
import click

from typing import Optional, List, Callable, Tuple

from tasdmc import config


class DataFiles:
    sdgeant = config.Global.data_dir / 'sdgeant.dst'
    atmos = config.Global.data_dir / 'atmos.bin'


config.Global.runs_dir.mkdir(exist_ok=True, parents=True)


def run_dir(run_name: Optional[str] = None) -> Path:
    run_name: str = run_name or config.get_key('name')
    return config.Global.runs_dir / run_name


_local_run_internal_dir_getters: List[Callable[[], Path]] = []


def internal_local_run_dir(fn):
    _local_run_internal_dir_getters.append(fn)
    return lru_cache()(fn)


# processing results directories


@internal_local_run_dir
def corsika_input_files_dir() -> Path:
    return run_dir() / 'corsika_input'


@internal_local_run_dir
def corsika_output_files_dir() -> Path:
    return run_dir() / 'corsika_output'


@internal_local_run_dir
def dethinning_output_files_dir() -> Path:
    return run_dir() / 'corsika_output_dethinned'


@internal_local_run_dir
def c2g_output_files_dir() -> Path:
    return run_dir() / 'corsika2geant_output'


@internal_local_run_dir
def events_dir() -> Path:
    return run_dir() / 'events'


@internal_local_run_dir
def spectral_sampled_events_dir() -> Path:
    return run_dir() / 'events_spectral_sampled'


@internal_local_run_dir
def reconstruction_dir() -> Path:
    return run_dir() / 'reconstruction'


@internal_local_run_dir
def final_dir() -> Path:
    return run_dir() / 'final'


# service directories


@internal_local_run_dir
def input_hashes_dir() -> Path:
    return run_dir() / '_input_files_hashes'


@internal_local_run_dir
def logs_dir() -> Path:
    return run_dir() / '_logs'


@internal_local_run_dir
def pipelines_failed_dir() -> Path:
    return logs_dir() / 'failed_pipelines'


# service files


def saved_main_pid_file():
    return run_dir() / 'main.pid'


def saved_run_config_file(run_name: Optional[str] = None):
    return run_dir(run_name) / 'run.yaml'


def saved_nodes_config_file(run_name: Optional[str] = None):
    return run_dir(run_name) / 'nodes.yaml'


# log files


def system_resources_log():
    return logs_dir() / 'system_resources.log'


def multiprocessing_log():
    return logs_dir() / 'multiprocessing.log'


def cards_gen_info_log():
    return logs_dir() / 'cards_generation_info.log'


def pipelines_log():
    return logs_dir() / 'pipelines.log'


def pipeline_failed_file(pipeline_id: str):
    return pipelines_failed_dir() / f'{pipeline_id}.failed'


def input_hashes_debug_log():
    return logs_dir() / 'input_hashes_debug.log'


def file_checks_debug_log():
    return logs_dir() / 'file_checks_debug.log'


def routine_cmd_debug_log():
    return logs_dir() / 'routine_cmd_debug.log'


# top-level functions


def prepare_run_dir(continuing: bool = False):
    rd = run_dir()
    if continuing:
        rd.mkdir(exist_ok=True)
    else:
        try:
            rd.mkdir()
            click.echo(f"Run directory created: {rd.absolute()}")
        except FileExistsError as fee:
            raise ValueError(
                f"Run '{rd.name}' already exists, pick another run name. "
                + f"To continue aborted run, use 'tasdmc continue {rd.name}'"
            ) from fee
    if logs_dir().exists():
        old_logs_dir_name = f'before-{datetime.utcnow().isoformat(timespec="seconds")}'
        old_logs_dir = logs_dir() / old_logs_dir_name
        old_logs_dir.mkdir()
        for old_log in logs_dir().glob('*'):
            if not old_log.name.startswith('before'):
                shutil.move(old_log, old_logs_dir / old_log.name)

    config.RunConfig.dump(saved_run_config_file())

    if config.is_local_run():
        for dir_getter in _local_run_internal_dir_getters:
            dir_getter().mkdir(exist_ok=continuing)
    if config.is_distributed_run():
        config.NodesConfig.dump(saved_nodes_config_file())


def remove_run_dir():
    rd = run_dir()
    shutil.rmtree(rd, ignore_errors=True)
    click.echo(f"Run directory removed: {rd.absolute()}")


def save_main_process_pid():
    saved_main_pid_file().write_text(str(os.getpid()))  # saving currend main process ID


def get_previous_logs_dirs() -> List[Path]:
    before_dirs = []
    for d in logs_dir().iterdir():
        if d.is_dir() and d.name.startswith('before'):
            before_dirs.append(d)
    return before_dirs


def get_saved_main_pid():
    return int(saved_main_pid_file().read_text())


def get_config_paths(run_name: str) -> Tuple[Path, Path]:
    if not run_dir(run_name).exists():
        raise ValueError(f"Run '{run_name}' not found")
    return saved_run_config_file(run_name), saved_nodes_config_file(run_name)


def get_all_run_names() -> List[str]:
    return [rd.name for rd in config.Global.runs_dir.iterdir()]


def get_all_internal_dirs() -> List[Path]:
    return [idir_getter() for idir_getter in _local_run_internal_dir_getters]


# NOTE: THESE METHOD RELY ON HEURISTICS AND NAMING CONVENTIONS AND MAY
# BREAK IF STEPS ARE RECONFIGURED IN A NON-STANDARD WAY


def _all_failed_pipeline_files() -> List[Path]:
    return list(pipelines_failed_dir().glob('*.failed'))


def _pipeline_id_from_file(file: Path) -> str:
    return file.name.split('.')[0].split('_')[0]


def get_failed_pipeline_ids() -> List[str]:
    return [_pipeline_id_from_file(f) for f in _all_failed_pipeline_files()]


def get_all_pipeline_ids() -> List[str]:
    return [_pipeline_id_from_file(f) for f in corsika_input_files_dir().glob("*.in")]
