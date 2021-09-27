import os
import shutil
from pathlib import Path

from typing import Optional

from .config import Config, get_config_key


RUNS_DIR = os.environ.get("TASDMC_RUNS_DIR") or Path(os.getcwd()) / 'runs'
RUNS_DIR.mkdir(exist_ok=True)


run_dir_idx: Optional[int] = None


def run_dir(config: Config) -> Path:
    run_dir_name: str = get_config_key(config, 'name')
    if run_dir_idx is not None:
        run_dir_name += '-' + str(run_dir_idx)
    return RUNS_DIR / run_dir_name


def prepare_run_dir(config, read_config_filename):
    append_idx_if_exists = get_config_key(config, 'append_index_if_exists', default=False)
    if append_idx_if_exists:
        global run_dir_idx
        while True:
            rd = run_dir(config)
            try:
                rd.mkdir()
                break
            except FileExistsError:
                run_dir_idx = run_dir_idx + 1 if run_dir_idx is not None else 1

    run_configs_dir = rd / 'configs'
    run_configs_dir.mkdir()
    shutil.copy(read_config_filename, run_configs_dir / 'run.yaml')
