import psutil
from pathlib import Path


def available_ram() -> int:
    """Available RAM in Gb"""
    return psutil.virtual_memory().available / (1024 ** 3)


def n_cpu() -> int:
    return psutil.cpu_count()


def available_disk_space(where_file: Path) -> int:
    """Available disk space on the same partition as where_file in bytes"""
    partitions = [dp.mountpoint for dp in psutil.disk_partitions()]
    matching_partitions = []
    for partition in partitions:
        if where_file.match(partition + '/**'):
            matching_partitions.append(partition)

    longest_matching_partition = max(matching_partitions, key=len)
    return psutil.disk_usage(longest_matching_partition).free
