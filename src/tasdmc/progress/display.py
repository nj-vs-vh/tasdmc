import click
import re
from collections import defaultdict

from tasdmc import fileio


multiproc_debug_message_re = re.compile(r'.*\(pid (?P<pid>\d+)\)')


def print_multiprocessing_debug(n_messages: int):
    with open(fileio.multiprocessing_debug_log(), 'r') as f:
        lines = f.readlines()
    lines.reverse()

    lines_for_last_run_instance = []
    for l in lines:
        if '=======' in l:
            break
        lines_for_last_run_instance.append(l.strip())

    messages_by_pid = defaultdict(list)
    for line in lines_for_last_run_instance:
        if not line:
            continue

        m = multiproc_debug_message_re.match(line)
        if m is None:
            click.secho(f"Can't parse multiprocessing debug message {line}", fg='red')
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
