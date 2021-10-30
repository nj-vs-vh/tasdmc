import psutil
from pathlib import Path

from .utils import bytes2Gb


def available_ram() -> int:
    return bytes2Gb(psutil.virtual_memory().available)


def n_cpu() -> int:
    return psutil.cpu_count()


def available_disk_space(where_file: Path) -> int:
    return bytes2Gb(psutil.disk_usage(str(where_file)).free)


def directory_size(dir: Path) -> int:
    return bytes2Gb(sum(f.stat().st_size for f in dir.glob('**/*') if f.is_file()))
