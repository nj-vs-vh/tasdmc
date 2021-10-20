"""System resources monitoring module"""

import psutil
from pathlib import Path

import click


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


def kill_all_run_processes_by_main_process_id(pid: int):
    try:
        main_process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        click.echo(
            "Main process has already been killed! "
            + "If you have killed it directly with 'kill <pid>' or Ctrl+C, you might need to "
            + "find and kill all the child processes manually..."
        )
        return
    child_processes = main_process.children(recursive=True)
    for p in [*child_processes, main_process]:
        click.echo(f"Killing process {p.pid} ({p.name()})")
        p.terminate()
