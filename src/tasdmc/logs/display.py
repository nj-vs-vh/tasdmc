import click
import re
import os
from collections import defaultdict
from datetime import datetime, timedelta
import plotext as plt
import shutil

from typing import List

from tasdmc import fileio
from tasdmc.logs.step_progress import EventType, PipelineStepProgress
from tasdmc.logs.utils import str2datetime, datetime2str, timedelta2str
from tasdmc.logs import pipeline_progress


def print_multiprocessing_log(n_messages: int):
    multiproc_debug_message_re = re.compile(r'.*\(pid (?P<pid>\d+)\)')
    lines_for_last_run = fileio.multiprocessing_log().read_text().splitlines()
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

    click.secho("\nMultiprocessing debug messages by process", bold=True)
    for pid in sorted(messages_by_pid.keys()):
        click.secho(f"Process {pid}:", bold=True)
        for line in messages_by_pid[pid]:
            if f"pid {pid}" in line:
                click.secho(line.strip(), dim=True)


def print_pipelines_progress():
    pipeline_stack_by_id = defaultdict(set)
    for pipeline_step_progress in PipelineStepProgress.load():
        pipeline_id = pipeline_step_progress.pipeline_id
        if pipeline_stack_by_id[pipeline_id] is None:  # pipeline has failed
            continue
        if pipeline_step_progress.event_type is EventType.STARTED:
            pipeline_stack_by_id[pipeline_id].add(pipeline_step_progress.step_input_hash)
        elif pipeline_step_progress.event_type is EventType.COMPLETED:
            pipeline_stack_by_id[pipeline_id].discard(pipeline_step_progress.step_input_hash)
        elif pipeline_step_progress.event_type is EventType.FAILED:
            pipeline_stack_by_id[pipeline_id] = None

    pipelines_total = sum(1 for _ in fileio.corsika_input_files_dir().iterdir())
    pipelines_failed = 0
    pipelines_completed = 0
    pipelines_running = 0
    for pipeline_id, stack in pipeline_stack_by_id.items():
        if pipeline_progress.is_failed(pipeline_id) or stack is None:
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
    progress_bar_width = os.get_terminal_size().columns
    for _, color, such_pipelines in display_data:
        click.secho("█" * int(progress_bar_width * such_pipelines / pipelines_total), nl=False, fg=color)
    click.echo('')
    for name, color, such_pipelines in display_data:
        click.echo(click.style("■", fg=color) + f" {name} ({such_pipelines} / {pipelines_total})")


def print_system_monitoring(include_previous_runs: bool = False, evaluation_time_as_x: bool = True):
    timestamps: List[datetime] = []
    cpu: List[float] = []
    mem: List[float] = []
    disk_used: List[float] = []
    disk_avl: List[float] = []

    logs_dirs_to_look_in = [fileio.logs_dir()]
    if include_previous_runs:
        logs_dirs_to_look_in.extend(fileio.get_previous_logs_dirs())
    system_resources_log_filename = fileio.system_resources_log().name

    entry_re = re.compile(
        r"^\[(?P<timestamp>.*?)\] CPU (?P<cpu_perc>.*?) MEM (?P<mem_usage>.*?) "
        + r"DISK (?P<disk_used_by_run>.*?)/(?P<disk_available>.*?)$"
    )

    run_start_indices: List[int] = [0]
    for logs_dir in logs_dirs_to_look_in:
        system_resources_log = logs_dir / system_resources_log_filename
        if not system_resources_log.exists():
            continue
        n_entries_before = len(timestamps)
        for entry in system_resources_log.read_text().splitlines():
            m = entry_re.match(entry)
            try:
                entry_timestamp = str2datetime(m.group('timestamp'))
                cpu_entry = sum(
                    [float(cpu_per_worker) for cpu_per_worker in m.group('cpu_perc').split() if cpu_per_worker]
                )
                mem_entry = sum(
                    [float(mem_per_worker) for mem_per_worker in m.group('mem_usage').split() if mem_per_worker]
                )
                disk_used_entry = float(m.group('disk_used_by_run'))
                disk_avl_entry = float(m.group('disk_available'))

                timestamps.append(entry_timestamp)
                cpu.append(cpu_entry)
                mem.append(mem_entry)
                disk_used.append(disk_used_entry)
                disk_avl.append(disk_avl_entry)
            except Exception:
                click.secho(f"Can't parse system resources log entry: '{entry}'")
        n_entries_after = len(timestamps)
        if n_entries_after > n_entries_before:
            run_start_indices.append(n_entries_after)  # next run will/would start here
    if not timestamps:
        click.echo("No recorded system resources found for the run")
        return

    run_start_indices = run_start_indices[:-1]

    if include_previous_runs:
        cpu = [t[1] for t in sorted(zip(timestamps, cpu))]
        mem = [t[1] for t in sorted(zip(timestamps, mem))]
        disk_used = [t[1] for t in sorted(zip(timestamps, disk_used))]
        disk_avl = [t[1] for t in sorted(zip(timestamps, disk_avl))]
        run_start_timestamps = sorted([timestamps[i] for i in run_start_indices])
        timestamps.sort()
        run_start_indices = [timestamps.index(rst) for rst in run_start_timestamps]

    click.echo(f"System resources (as last monitored at {datetime2str(timestamps[-1])}):")
    click.echo(f"Total CPU utilization (100% is 1 fully utilized core): {cpu[-1]:.2f}%")
    click.echo(f"Total memory consumed: {mem[-1]:.2f} Gb")
    click.echo(f"Disk used: {disk_used[-1]:.2f} Gb")
    if len(timestamps) < 5:
        click.echo("Plots are not available for less than 5 recorded data points")
        return

    if evaluation_time_as_x:
        # converting timestamps (absolute times) to evaluation time as if all runs run without
        # pauses between them; x axis then represents "run evaluation time" (RET)
        run_eval_times: List[timedelta] = timestamps.copy()
        previous_runs_evaluation_time = timedelta(seconds=0)
        for run_start_i, run_end_i in zip(run_start_indices, [*run_start_indices[1:], len(run_eval_times)]):
            run_start_dt = run_eval_times[run_start_i]
            for i in range(run_start_i, run_end_i):
                run_eval_times[i] = (run_eval_times[i] - run_start_dt) + previous_runs_evaluation_time
            previous_runs_evaluation_time = run_eval_times[i] + timedelta(
                minutes=1
            )  # as if there was 1 min between runs
        xs = [t.total_seconds() for t in run_eval_times]
        tick_label_from_value = lambda x: timedelta2str(timedelta(seconds=x))
        x_axis_label = "Run evaluation time"
    else:
        xs = [dt.timestamp() for dt in timestamps]
        tick_label_from_value = lambda x: datetime2str(datetime.fromtimestamp(x))
        x_axis_label = "Datetime, UTC"

    x_n = len(xs)
    x_tick_indices = [0, int(0.33 * x_n), int(0.66 * x_n), x_n - 1]
    x_ticks = [xs[idx] for idx in x_tick_indices]
    x_tick_labels = [tick_label_from_value(xs[idx]) for idx in x_tick_indices]

    terminal_width, terminal_height = shutil.get_terminal_size()
    plot_width, plot_height = min(100, terminal_width), min(30, terminal_height)

    plt.clear_figure()
    plt.subplots(3, 1)

    # disk usage plot
    plt.subplot(1, 1)
    # plotting available disk space only whan we're running out of it (< 3 Gb left)
    disk_avl_plot_data = [(t, da + du) for t, da, du in zip(xs, disk_avl, disk_used) if da < 3]
    plt.plot(xs, disk_used, color='blue', label="Run directory" if disk_avl_plot_data else "")
    if disk_avl_plot_data:
        plt.plot(
            [td[0] for td in disk_avl_plot_data],
            [td[1] for td in disk_avl_plot_data],
            color='red',
            label="Max for run directory",
        )
    plt.title("Disk usage")
    plt.ylabel("Disk usage, Gb")
    plt.xlabel(x_axis_label)
    plt.plotsize(plot_width, plot_height)
    plt.xticks(x_ticks, x_tick_labels)

    plt.subplot(2, 1)
    plt.plot(xs, cpu, color='green')
    plt.title("CPU utilization")
    plt.ylabel("CPU, 100% per core")
    plt.xlabel(x_axis_label)
    plt.plotsize(plot_width, plot_height)
    plt.xticks(x_ticks, x_tick_labels)

    plt.subplot(3, 1)
    plt.plot(xs, mem, color='teal')
    plt.title("Memory usage")
    plt.ylabel("RAM used, Gb")
    plt.xlabel(x_axis_label)
    plt.plotsize(plot_width, plot_height)
    plt.xticks(x_ticks, x_tick_labels)

    plt.show(allow_scrolling=True)


if __name__ == "__main__":
    from tasdmc import config

    config.RunConfig.load(fileio.get_run_config_path("test-run"))
    print_system_monitoring(True, True)
