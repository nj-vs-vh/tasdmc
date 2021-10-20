"""Access to configuration read from .yaml file(s)

This module serves as a global singleton object:
>>> from tasdmc import config
>>> config.get_key('your.key.here')
"""

import yaml
from pathlib import Path
import os

from typing import Any, Optional, List, Type

from tasdmc import system


_config = None


class ConfigNotReadError(Exception):
    pass


class ConfigKeyError(KeyError):
    pass


class BadConfigValue(ValueError):
    pass


class Global:
    """Namespace class to hold global/pre-installation configuration options"""

    bin_dir = Path(os.environ['TASDMC_BIN_DIR'])
    runs_dir = Path(os.environ['TASDMC_RUNS_DIR'])
    sdanalysis_dir = Path(os.environ['SDANALYSIS_DIR'])
    memory_per_process_Gb = float(os.environ['TASDMC_MEMORY_PER_PROCESS_GB'])
    data_dir = Path(os.environ['TASDMC_DATA_DIR'])


def load(filename: str):
    global _config
    with open(filename, 'r') as f:
        _config = yaml.safe_load(f)


def dump(filename: Path):
    with open(filename, 'w') as f:
        yaml.dump(_config, f)


def validate(steps: Optional[List[Type['FileInFileOutStep']]] = None):  # type: ignore
    if steps is None:
        from tasdmc.steps import all_steps as steps
    for Step in steps:
        Step.validate_config()


_RAISE_ERROR_ON_MISSING_KEY = object()


def get_key(key: str, key_prefix: Optional[str] = None, default: Optional[Any] = _RAISE_ERROR_ON_MISSING_KEY) -> Any:
    """Utility function to get (possibly deeply nested) key from configand get nice error messages
    in case something is wrong.

    Args:
        key (str): comma-separated list of keys from top to bottom, e.g. 'infiles.log10E.step'
        key_prefix (str): prefix added to the start of the key, e.g. for 'infiles' prefix any 'smth' key
                          becomes 'infiles.smth'

    Raises:
        ConfigKeyError: specified key is missing on some nesting level, error message tells what is wrong
        ConfigNotReadError: get_key was called before load()

    Returns:
        Any: value in the specified key
    """
    if _config is None:
        raise ConfigNotReadError(f"Attempt to read config key before it is loaded, run config.load('smth.yaml') first.")

    if key_prefix is not None:
        key = key_prefix + '.' + key
    level_keys = key.split('.')
    if not level_keys:
        raise ConfigKeyError(f'No key specified')

    traversed_level_keys = []
    current_value = _config
    for level_key in level_keys:
        current_value = current_value.get(level_key)
        if current_value is None:
            if default is _RAISE_ERROR_ON_MISSING_KEY:
                raise ConfigKeyError(
                    f"Config does not contain top-level '{level_key}' key"
                    if not traversed_level_keys
                    else f"Subconfig '{'.'.join(traversed_level_keys)}' does not contain required '{level_key}' key"
                )
            else:
                return default
        else:
            traversed_level_keys.append(level_key)

    return current_value


def run_name() -> str:
    return get_key('name')


def try_to_continue() -> bool:
    return get_key('if_exists') == 'continue'


def used_processes() -> int:
    max_processes_explicit = get_key('resources.max_processes', default=-1)
    max_memory_explicit = get_key('resources.max_memory', default=-1)
    if max_memory_explicit == max_processes_explicit == -1:
        return 1  # if nothing specified, no parallelization
    if 0 < max_memory_explicit < Global.memory_per_process_Gb:
        raise BadConfigValue(
            f"Memory constraint is too tight! {max_memory_explicit} Gb is less "
            + f"than a single-thread requirement ({Global.memory_per_process_Gb} Gb)"
        )
    max_processes_inferred = int(max_memory_explicit / Global.memory_per_process_Gb)
    max_processes_variants = [np for np in [max_processes_explicit, max_processes_inferred, system.n_cpu()] if np > 0]
    return min(max_processes_variants)


def used_ram() -> int:
    return used_processes() * Global.memory_per_process_Gb
