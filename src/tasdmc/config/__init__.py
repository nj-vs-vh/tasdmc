"""Access to configuration read from .yaml file(s)

This module serves as a global singleton object:
>>> from tasdmc import config
>>> config.get_key('my.special.key')
"""

from pathlib import Path
import os
import sys

from typing import Any, Optional, List, Type

from tasdmc.utils import get_dot_notation, NO_DEFAULT
from .exceptions import BadConfigValue
from .storage import RunConfig, NodesConfig


class Global:
    """Namespace class holding global/pre-installation configuration options"""

    runs_dir: Path
    data_dir: Path
    bin_dir: Path
    memory_per_process_Gb: float

    @classmethod
    def load(cls):
        try:
            cls.runs_dir = Path(os.environ['TASDMC_RUNS_DIR'])
            cls.data_dir = Path(os.environ['TASDMC_DATA_DIR'])
            cls.bin_dir = Path(os.environ['TASDMC_BIN_DIR'])
            cls.memory_per_process_Gb = float(os.environ['TASDMC_MEMORY_PER_PROCESS_GB'])
        except KeyError as e:
            missing_env_var = str(e).strip('\'')
            print(f"Can't load global tasdmc config, env variable is missing: {missing_env_var}")
            sys.exit()


Global.load()


class Ephemeral:
    """Namespace class holding emphemeral (= not persistent) config values coming from command-line params"""

    rerun_step_on_input_hash_mismatch: bool = False
    disable_input_hash_checks: bool = False
    safe_abort_in_progress: bool = False


def validate(step_classes: Optional[List[Type['PipelineStep']]] = None):  # type: ignore
    from tasdmc.steps.corsika_cards_generation import validate_config

    validate_config()

    assert not (Ephemeral.rerun_step_on_input_hash_mismatch and Ephemeral.disable_input_hash_checks), "Can't be both!"
    if step_classes is None:
        from tasdmc.steps import all_steps as step_classes
    for Step in step_classes:
        try:
            Step.validate_config()
        except Exception as e:
            raise BadConfigValue(f"Config validation for {Step.__name__} failed: {e}") from e


def get_key(key: str, default: Optional[Any] = NO_DEFAULT) -> Any:
    """Main function to access config"""
    return get_dot_notation(RunConfig.loaded().contents, key, default=default)


def run_name() -> str:
    rc: RunConfig = RunConfig.loaded()
    return rc.name


def is_distributed_run() -> bool:
    assert RunConfig.is_loaded()
    return NodesConfig.is_loaded()


def is_local_run() -> bool:
    return not is_distributed_run()