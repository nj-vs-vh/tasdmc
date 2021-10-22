import click
import re
import os
from collections import defaultdict
from pathlib import Path
from io import StringIO
import yaml

from typing import List

from tasdmc import fileio
from tasdmc.progress.step_progress import EventType, PipelineStepProgress
from tasdmc.progress import pipeline_progress


multiproc_debug_message_re = re.compile(r'.*\(pid (?P<pid>\d+)\)')


def print_multiprocessing_debug(n_messages: int):
    lines_for_last_run = _get_last_run_lines(fileio.multiprocessing_debug_log())
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


def load_pipeline_steps(pipeline_id: str) -> List[PipelineStepProgress]:
    last_run_progress = _get_last_run_lines(fileio.pipeline_log(pipeline_id))
    return [
        PipelineStepProgress.load(dump, pipeline_id) for dump in yaml.safe_load(StringIO('\n'.join(last_run_progress)))
    ]


def print_pipelines_progress():
    pipelines_total = 0
    pipelines_failed = 0
    pipelines_pending = 0
    pipelines_completed = 0
    pipelines_running = 0
    for pipeline_file in fileio.pipeline_logs_dir().glob(fileio.pipeline_log('*').name):
        pipelines_total += 1
        pipeline_id = pipeline_file.stem
        if pipeline_progress.is_failed(pipeline_id):
            pipelines_failed += 1
            continue
        pipeline_steps = load_pipeline_steps(pipeline_id)
        if len(pipeline_steps) == 0:
            pipelines_pending += 1
            continue
        step_stack = set()
        for step_progress in pipeline_steps:
            if step_progress.event_type is EventType.STARTED:
                step_stack.add(step_progress.step_input_hash)
            elif step_progress.event_type is EventType.COMPLETED:
                step_stack.discard(step_progress.step_input_hash)
            elif step_progress.event_type is EventType.FAILED:
                pipelines_failed += 1
                break
        else:  # if not broken out on failed
            if len(step_stack) == 0:
                # completed if all (logged) steps in a pipeline were started and completed
                # this can overestimate number of completed steps if one ended and
                # the other hasn't started yet but we'll ignore it for now
                pipelines_completed += 1
            else:
                pipelines_running += 1
    error = pipelines_total - (pipelines_completed + pipelines_failed + pipelines_running + pipelines_pending)
    if error:
        click.echo(f"Error in pipeline count: {error} pipelines with unknown status. Counting them as pending.")
    pipelines_pending += error
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


def _get_last_run_lines(log_filename: Path) -> List[str]:
    lines_from_last_run = []
    with open(log_filename, 'r') as f:
        for line in f:
            line = line.strip('\n')
            if line == fileio.RUN_LOG_SEPARATOR:
                lines_from_last_run.clear()
            else:
                lines_from_last_run.append(line)
    return lines_from_last_run
