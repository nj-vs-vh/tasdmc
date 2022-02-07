import psutil
from pathlib import Path

from tasdmc import config
from tasdmc.config.exceptions import BadConfigValue
from .utils import bytes2Gb


def available_ram() -> int:
    return bytes2Gb(psutil.virtual_memory().available)


def n_cpu() -> int:
    return psutil.cpu_count()


def available_disk_space(where_file: Path) -> int:
    return bytes2Gb(psutil.disk_usage(str(where_file)).free)


def directory_size(dir: Path) -> int:
    return bytes2Gb(sum(f.stat().st_size for f in dir.glob('**/*') if f.is_file()))


def used_processes() -> int:
    max_processes_explicit = config.get_key('resources.max_processes', default=-1)
    max_memory_explicit = config.get_key('resources.max_memory', default=-1)
    if max_memory_explicit == max_processes_explicit == -1:
        return 1  # if nothing specified, no parallelization
    if 0 < max_memory_explicit < config.Global.memory_per_process_Gb:
        raise BadConfigValue(
            f"Memory constraint is too tight! {max_memory_explicit} Gb is less "
            + f"than a single-thread requirement ({config.Global.memory_per_process_Gb} Gb)"
        )
    max_processes_inferred = int(max_memory_explicit / config.Global.memory_per_process_Gb)
    max_processes_variants = [
        np for np in [max_processes_explicit, max_processes_inferred, n_cpu()] if np > 0
    ]
    return min(max_processes_variants)


def used_ram() -> int:
    return used_processes() * config.Global.memory_per_process_Gb
