import click
import re
import os
from collections import defaultdict

from tasdmc import fileio
from tasdmc.progress.step_progress import EventType, PipelineStepProgress


multiproc_debug_message_re = re.compile(r'.*\(pid (?P<pid>\d+)\)')


def print_multiprocessing_debug(n_messages: int):
    lines_for_last_run = fileio.multiprocessing_debug_log().read_text().splitlines()
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


def count_pipelines():
    return sum(1 for _ in fileio.corsika_input_files_dir().iterdir())


def print_pipelines_progress():
    pipeline_stack_by_id = defaultdict(set)
    for pipeline_step_progress in PipelineStepProgress.load():
        plid = pipeline_step_progress.pipeline_id
        if pipeline_stack_by_id[plid] is None:  # pipeline has failed
            continue
        if pipeline_step_progress.event_type is EventType.STARTED:
            pipeline_stack_by_id[plid].add(pipeline_step_progress.step_input_hash)
        elif pipeline_step_progress.event_type is EventType.COMPLETED:
            pipeline_stack_by_id[plid].discard(pipeline_step_progress.step_input_hash)
        elif pipeline_step_progress.event_type is EventType.FAILED:
            pipeline_stack_by_id[plid] = None

    pipelines_total = count_pipelines()
    pipelines_failed = 0
    pipelines_completed = 0
    pipelines_running = 0
    for plid, stack in pipeline_stack_by_id.items():
        if stack is None:
            pipelines_failed += 1
        elif len(stack) == 0:
            pipelines_completed += 1
        else:
            pipelines_running += 1
    pipelines_pending = pipelines_total - (pipelines_failed + pipelines_completed + pipelines_running)
    display_data = [
        ('completed', 'green', pipelines_completed),
        ('running', 'yellow', pipelines_running),
        ('pending', 'white', pipelines_pending),
        ('failed', 'red', pipelines_failed),
    ]
    progress_bar_width = os.get_terminal_size().columns - 2
    click.echo(" ", nl=False)
    for _, color, such_pipelines in display_data:
        click.secho("█" * int(progress_bar_width * such_pipelines / pipelines_total), nl=False, fg=color)
    click.echo('')
    for name, color, such_pipelines in display_data:
        click.echo(click.style("■", fg=color) + f" {name} ({such_pipelines} / {pipelines_total})")
