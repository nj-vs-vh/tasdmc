import click
import re
from collections import defaultdict
from pathlib import Path

from typing import List

from tasdmc import fileio


multiproc_debug_message_re = re.compile(r'.*\(pid (?P<pid>\d+)\)')


def print_multiprocessing_debug(n_messages: int):
    lines_for_last_run = get_last_run_lines(fileio.multiprocessing_debug_log())
    lines_for_last_run.reverse()

    messages_by_pid = defaultdict(list)
    for line in lines_for_last_run:
        if not line:
            continue

        m = multiproc_debug_message_re.match(line)
        if m is None:
            click.secho(f"Can't parse multiprocessing debug message '{line}'", fg='red')
            continue

        pid = int(m.groupdict()['pid'])
        if len(messages_by_pid[pid]) >= n_messages:
            continue
        else:
            messages_by_pid[pid].insert(0, line)

    click.secho(f"\nMultiprocessing debug messages by process", bold=True)
    for pid in sorted(messages_by_pid.keys()):
        click.secho(f"Process {pid}:", bold=True)
        for line in messages_by_pid[pid]:
            if f"pid {pid}" in line:
                click.secho(line.strip(), dim=True)


def get_last_run_lines(log_filename: Path) -> List[str]:
    lines_from_last_run = []
    with open(log_filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line == fileio.RUN_LOG_SEPARATOR:
                lines_from_last_run.clear()
            else:
                lines_from_last_run.append(line)
    return lines_from_last_run
