import click

from typing import List

from tasdmc import fileio


def print_multiprocessing_debug(pids: List[int], n_messages: int):
    with open(fileio.multiprocessing_debug_log(), 'r') as f:
        lines = f.readlines()
    lines.reverse()
    click.secho(f"\nMultiprocessing debug messages by process", bold=True)
    for pid in sorted(pids):
        messages_printed = 0
        click.secho(f"Process {pid}:", bold=True)
        for line in lines:
            if f"pid {pid}" in line:
                click.secho(line.strip(), dim=True)
                messages_printed += 1
            if messages_printed >= n_messages:
                break
