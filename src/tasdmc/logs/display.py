from __future__ import annotations
from multiprocessing.sharedctypes import Value

import click
import re
import os
from collections import defaultdict
from datetime import datetime, timedelta
import plotext as plt
import shutil
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from functools import partial
from itertools import chain
import math

from typing import List, Optional, TypeVar, Type, Dict, Set

from tasdmc import fileio
from tasdmc.steps.corsika_cards_generation import generate_corsika_cards
from tasdmc.pipeline import get_steps_queue
from tasdmc.logs.step_progress import EventType, PipelineStepProgress
from tasdmc.logs.utils import str2datetime, datetime2str, timedelta2str


def print_multiprocessing_log(n_messages: int):
    multiproc_debug_message_re = re.compile(r'.*\(pid (?P<pid>\d+)\)')
    lines_for_last_run = fileio.multiprocessing_log().read_text().splitlines()
    lines_for_last_run.reverse()

    messages_by_pid: Dict[int, List[str]] = defaultdict(list)
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


_T = TypeVar("_T")


@dataclass
class LogData:
    node_name: Optional[str]

    def dump(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def load(cls: Type[_T], dump: str) -> _T:
        return cls(**json.loads(dump))

    def echo_node_name(self):
        if self.node_name is not None:
            click.secho(self.node_name, bold=True)


@dataclass
class PipelineProgress(LogData):
    completed: int
    running: int
    pending: int
    failed: int
    running_now_count: Dict[str, int]
    step_order: List[str]

    def __add__(self, other: PipelineProgress) -> PipelineProgress:
        if not isinstance(other, PipelineProgress):
            return NotImplemented
        assert self.step_order == other.step_order, "Can't sum PipelineProgress with diferent step orderings"
        return PipelineProgress(
            completed=self.completed + other.completed,
            running=self.running + other.running,
            pending=self.pending + other.pending,
            failed=self.failed + other.failed,
            running_now_count={
                step_name: n + other.running_now_count[step_name] for step_name, n in self.running_now_count.items()
            },
            step_order=self.step_order,
            node_name=(f"{self.node_name} + {other.node_name}") if self.node_name and other.node_name else None,
        )

    @classmethod
    def parse_from_log(cls) -> PipelineProgress:
        failed_pipelines: Set[str] = set()
        started_pipelines: Set[str] = set()
        last_completed_step_by_pipeline: Dict[str, str] = dict()
        last_started_step_by_pipeline: Dict[str, str] = dict()
        for step_progress in PipelineStepProgress.load():
            pipeline_id = step_progress.pipeline_id
            started_pipelines.add(pipeline_id)
            if step_progress.event_type is EventType.FAILED:
                failed_pipelines.add(pipeline_id)
            elif step_progress.event_type is EventType.STARTED:
                last_started_step_by_pipeline[pipeline_id] = step_progress.step_name
            elif step_progress.event_type in {EventType.COMPLETED, EventType.SKIPPED}:
                last_completed_step_by_pipeline[pipeline_id] = step_progress.step_name

        n_total = len(generate_corsika_cards(logging=False, dry=True))
        n_failed = len(failed_pipelines)
        n_pending = n_total - len(started_pipelines)
        n_running_and_completed = len(started_pipelines.difference(failed_pipelines))

        step_order = [
            step.name
            for step in get_steps_queue(
                corsika_card_paths=[Path("dummy")],
                include_aggregation_steps=False,
                disable_batching=True,
            )
        ]
        # removing duplicates, leaving only first occurrence
        step_order = [name for i, name in enumerate(step_order) if name not in step_order[:i]]

        final_step = step_order[-1]
        completed_pipelines = {
            pipeline_id
            for pipeline_id, last_completed_step in last_completed_step_by_pipeline.items()
            if last_completed_step == final_step
        }
        n_completed = len(completed_pipelines)
        n_running = n_running_and_completed - n_completed

        n_running_by_step = dict.fromkeys(step_order, 0)

        for pipeline_id in started_pipelines:
            if pipeline_id in completed_pipelines or pipeline_id in failed_pipelines:
                continue
            last_started_step = last_started_step_by_pipeline.get(pipeline_id)
            last_completed_step = last_completed_step_by_pipeline.get(pipeline_id)
            if (
                last_started_step is None or last_started_step == last_completed_step
            ):  # the step is waiting in queue, count nex step as started
                running_now_step = step_order[step_order.index(last_completed_step) + 1]
            else:
                running_now_step = last_started_step
            n_running_by_step[running_now_step] += 1

        return PipelineProgress(
            completed=n_completed,
            running=n_running,
            pending=n_pending,
            failed=n_failed,
            running_now_count=n_running_by_step,
            step_order=step_order,
            node_name=None,
        )

    def print(self, with_node_name: bool = False, full_color: bool = True):
        if with_node_name:
            self.echo_node_name()

        colors = [
            (22, 145, 25) if full_color else "green",
            (232, 210, 9) if full_color else "yellow",
            (186, 186, 186) if full_color else "white",
            (199, 78, 52) if full_color else "red",
        ]

        def lerp_color(c1, c2, fraction: float):
            if not full_color:
                return c2
            lerp = []
            for idx in range(3):
                delta = c2[idx] - c1[idx]
                lerp.append(int(c1[idx] + delta * fraction))
            return tuple(lerp)

        labels = [
            "completed",
            "running",
            "pending",
            "failed",
        ]
        pipeline_counts = [self.completed, self.running, self.pending, self.failed]

        screen_width = os.get_terminal_size().columns

        def to_char_counts(counts: List[int]):
            total = sum(counts)
            char_counts = [math.ceil(screen_width * count / total) for count in counts]
            char_counts[char_counts.index(max(char_counts))] -= sum(char_counts) - screen_width
            return char_counts

        # general completed/running/pending/failed progress bar
        pipeline_char_counts = to_char_counts(pipeline_counts)
        for color, char_count in zip(colors, pipeline_char_counts):
            click.secho("█" * char_count, nl=False, fg=color)
        click.echo()

        # detalization of 'running' category by steps
        step_labels = self.step_order[::-1]  # from later to earlier steps
        step_counts = [self.running_now_count[l] for l in step_labels]
        step_colors = [
            lerp_color(colors[0], colors[1], (i + 1) / (len(step_labels) + 2)) for i, _ in enumerate(step_labels)
        ]

        # detalization of 'running' in a separate progress sub-bar, supported only when printing in full color
        if self.running > 0 and full_color:
            #   otherwise ascii bracket looks all jagged
            if self.completed > 0 and self.pending + self.failed > 0:
                for row_idx in range(3):
                    ascii_bracket_row = (
                        ("┌" if row_idx == 1 else (" " if row_idx == 0 else "|"))
                        + ("─" if row_idx == 1 else " ") * (pipeline_char_counts[0] - 1)
                        + ("┘" if row_idx == 1 else ("|" if row_idx == 0 else " "))
                        + " " * (pipeline_char_counts[1] - 2)
                        + ("└" if row_idx == 1 else ("|" if row_idx == 0 else " "))
                        + ("─" if row_idx == 1 else " ")
                        * (screen_width - pipeline_char_counts[0] - pipeline_char_counts[1] - 1)
                        + ("┐" if row_idx == 1 else (" " if row_idx == 0 else "|"))
                    )
                    click.echo(ascii_bracket_row)
            else:
                click.echo("\nRunning steps:")
            for step_color, char_count in zip(step_colors, to_char_counts(step_counts)):
                click.secho("█" * char_count, nl=False, fg=step_color)
            click.echo()

        click.echo()

        # legend for above progress bar/bars
        for name, color, count in zip(labels, colors, pipeline_counts):
            click.echo(click.style(" ■", fg=color) + f" {name} ({count} / {sum(pipeline_counts)})")
            if name == 'running':
                for step_label, step_color, step_count in zip(step_labels, step_colors, step_counts):
                    click.echo(
                        click.style("   ■", fg=step_color) + f" {step_label} ({step_count} / {sum(step_counts)})"
                    )


@dataclass
class SystemResourcesTimeline(LogData):
    timestamps: List[datetime]
    ret: List[timedelta]
    cpu: List[float]
    mem: List[float]
    disk_used: List[float]
    disk_avl: List[float]
    disk_read_speed: List[float]
    disk_write_speed: List[float]

    def __post_init__(self):
        assert len(self.timestamps) > 0, f"{self.__class__.__name__} must contain at least one measurement"
        for timeseries in (
            self.ret,
            self.cpu,
            self.mem,
            self.disk_used,
            self.disk_avl,
            self.disk_read_speed,
            self.disk_write_speed,
        ):
            assert len(timeseries) == len(
                self.timestamps
            ), f"{self.__class__.__name__} must contain length-aligned lists"

    def dump(self) -> str:
        d = asdict(self)
        d['timestamps'] = [dt.timestamp() for dt in self.timestamps]
        d['ret'] = [td.total_seconds() for td in self.ret]
        return json.dumps(d)

    @classmethod
    def load(cls, dump: str) -> SystemResourcesTimeline:
        data = json.loads(dump)
        data['timestamps'] = [datetime.fromtimestamp(dt_ts) for dt_ts in data['timestamps']]
        data['ret'] = [timedelta(seconds=td_ts) for td_ts in data['ret']]
        return SystemResourcesTimeline(**data)

    @property
    def start_timestamp(self) -> datetime:
        return self.timestamps[0]

    @property
    def end_timestamp(self) -> datetime:
        return self.timestamps[-1]

    def concatenate(
        self, other: SystemResourcesTimeline, ret_delay: timedelta = timedelta(minutes=1.0)
    ) -> SystemResourcesTimeline:
        assert self.end_timestamp < other.start_timestamp, "Can concatenate only later non-overlapping timeline"
        other_ret_offsetted = [self.ret[-1] + ret_delay + td for td in other.ret]
        return SystemResourcesTimeline(
            timestamps=self.timestamps + other.timestamps,
            ret=self.ret + other_ret_offsetted,
            cpu=self.cpu + other.cpu,
            mem=self.mem + other.mem,
            disk_used=self.disk_used + other.disk_used,
            disk_avl=self.disk_avl + other.disk_avl,
            disk_read_speed=self.disk_read_speed + other.disk_read_speed,
            disk_write_speed=self.disk_write_speed + other.disk_write_speed,
            node_name=self.node_name,
        )

    @classmethod
    def parse_from_logs(cls, include_previous_runs: bool) -> SystemResourcesTimeline:
        logs_dirs_to_look_in = [fileio.logs_dir()]
        if include_previous_runs:
            logs_dirs_to_look_in.extend(fileio.get_previous_logs_dirs())
        srts = [cls._parse_from_log(logs_dir) for logs_dir in logs_dirs_to_look_in]
        srts = [srt for srt in srts if srt is not None]
        if not srts:
            raise ValueError("No system resources logs parsed")
        srts.sort(key=lambda srt: srt.start_timestamp)
        concat_srt = None
        for srt in srts:
            if srt is None:
                continue
            if concat_srt is None:
                concat_srt = srt
            else:
                concat_srt = concat_srt.concatenate(srt)
        if concat_srt is None:
            raise ValueError("Error concatenating several system resources timelines")
        return concat_srt

    @classmethod
    def _parse_from_log(cls, logs_dir: Path) -> Optional[SystemResourcesTimeline]:
        system_resources_log = logs_dir / fileio.system_resources_log().name
        if not system_resources_log.exists():
            return None

        timestamps: List[datetime] = []
        cpu: List[float] = []
        mem: List[float] = []
        disk_used: List[float] = []
        disk_avl: List[float] = []
        disk_read: List[float] = []
        disk_write: List[float] = []

        entry_re = re.compile(
            r"^\[(?P<timestamp>.*?)\] CPU (?P<cpu_perc>.*?) MEM (?P<mem_usage>.*?) "
            + r"DISK (?P<disk_used_by_run>.*?)/(?P<disk_available>.*?)"
            + r"( DISKR (?P<disk_read>.*?) DISKW (?P<disk_write>.*?))?"  # optional: missing for old logs
            + r"$"
        )

        with open(system_resources_log, 'r') as srl:
            for entry_line in srl:
                entry_line = entry_line.strip()
                m = entry_re.match(entry_line)
                try:

                    def sum_proc_values_from_group(groupname: str) -> float:
                        group_match: Optional[str] = m.group(groupname)
                        if group_match is None:
                            return 0.0  # default for missing fields
                        return sum(float(proc_value) for proc_value in group_match.split() if proc_value)

                    timestamps_entry = str2datetime(m.group('timestamp'))
                    cpu_entry = sum_proc_values_from_group("cpu_perc")
                    mem_entry = sum_proc_values_from_group("mem_usage")
                    disk_used_entry = float(m.group('disk_used_by_run'))
                    disk_avl_entry = float(m.group('disk_available'))
                    disk_read_entry = sum_proc_values_from_group("disk_read")
                    disk_write_entry = sum_proc_values_from_group("disk_write")

                    timestamps.append(timestamps_entry)
                    cpu.append(cpu_entry)
                    mem.append(mem_entry)
                    disk_used.append(disk_used_entry)
                    disk_avl.append(disk_avl_entry)
                    disk_read.append(disk_read_entry)
                    disk_write.append(disk_write_entry)
                except Exception as e:
                    click.secho(f"Can't parse system resources log entry: '{entry_line}': {e}")
        if len(timestamps) == 0:
            return None
        run_times = [t - timestamps[0] for t in timestamps]
        return SystemResourcesTimeline(
            timestamps=timestamps,
            ret=run_times,
            cpu=cpu,
            mem=mem,
            disk_used=disk_used,
            disk_avl=disk_avl,
            disk_read_speed=disk_read,
            disk_write_speed=disk_write,
            node_name=None,
        )

    @staticmethod
    def _get_plot_width_height():
        terminal_width, terminal_height = shutil.get_terminal_size()
        return min(120, terminal_width), min(40, terminal_height)

    def display(self, absolute_x_axis: bool, with_node_name: bool = False):
        if with_node_name:
            self.echo_node_name()
        click.echo(f"System resources (as last monitored at {datetime2str(self.timestamps[-1])}):")
        click.echo(f"Total CPU utilization (100% is 1 core): {self.cpu[-1]:.2f}%")
        click.echo(f"Total memory consumed: {self.mem[-1]:.2f} Gb")
        click.echo(f"Disk usage: {self.disk_used[-1]:.2f} / {self.disk_avl[-1]:.2f} Gb")
        click.echo(f"Disk IO rates: read {self.disk_read_speed[-1]:.2f}, write {self.disk_write_speed[-1]:.2f} Mb/sec")
        if len(self.timestamps) < 5:
            click.echo("Plots are not available for less than 5 recorded data points")
            return

        if absolute_x_axis:
            xs = [dt.timestamp() for dt in self.timestamps]
            tick_label_from_value = lambda x: datetime2str(datetime.fromtimestamp(x))
            x_axis_label = "Datetime, UTC"
            plot_fn = partial(plt.scatter, marker='big')
        else:
            xs = [td.total_seconds() for td in self.ret]
            tick_label_from_value = lambda x: timedelta2str(timedelta(seconds=x))
            x_axis_label = "Run time"
            plot_fn = plt.plot

        x_n = len(xs)
        x_tick_indices = [0, int(0.33 * x_n), int(0.66 * x_n), x_n - 1]
        x_ticks = [xs[idx] for idx in x_tick_indices]
        x_tick_labels = [tick_label_from_value(xs[idx]) for idx in x_tick_indices]

        plot_width, plot_height = self._get_plot_width_height()

        plt.clear_figure()
        plt.subplots(4, 1)

        # disk usage plot
        plt.subplot(1, 1)
        # plotting available disk space only whan we're running out of it (< 3 Gb left)
        max_disk_used_plot_data = [(t, da + du) for t, da, du in zip(xs, self.disk_avl, self.disk_used) if da < 3]
        plot_fn(xs, self.disk_used, color='blue', label="Run directory" if max_disk_used_plot_data else "")
        if max_disk_used_plot_data:
            plot_fn(
                [td[0] for td in max_disk_used_plot_data],
                [td[1] for td in max_disk_used_plot_data],
                color='red',
                label="Run directory cap",
            )
        plt.title("Disk usage")
        plt.ylabel("Disk usage, Gb")
        plt.xlabel(x_axis_label)
        plt.plotsize(plot_width, plot_height)
        plt.xticks(x_ticks, x_tick_labels)

        plt.subplot(2, 1)
        plot_fn(xs, self.disk_read_speed, color='basil', label="read")
        plot_fn(xs, self.disk_write_speed, color='tomato', label="write")
        plt.title("Disk IO rates")
        plt.ylabel("Mb/sec")
        plt.xlabel(x_axis_label)
        plt.plotsize(plot_width, plot_height)
        plt.xticks(x_ticks, x_tick_labels)

        plt.subplot(3, 1)
        plot_fn(xs, self.cpu, color='green')
        plt.title("CPU utilization")
        plt.ylabel("CPU, 100% per core")
        plt.xlabel(x_axis_label)
        plt.plotsize(plot_width, plot_height)
        plt.xticks(x_ticks, x_tick_labels)

        plt.subplot(4, 1)
        plot_fn(xs, self.mem, color='teal')
        plt.title("Memory usage")
        plt.ylabel("RAM used, Gb")
        plt.xlabel(x_axis_label)
        plt.plotsize(plot_width, plot_height)
        plt.xticks(x_ticks, x_tick_labels)

        plt.show(allow_scrolling=True)

    @classmethod
    def display_multiple(cls, timelines: List[SystemResourcesTimeline]):
        all_timestamps_epoch = set(
            int(ts.timestamp()) for ts in chain.from_iterable([tl.timestamps for tl in timelines])
        )
        min_global_epoch = min(all_timestamps_epoch)
        max_global_epoch = max(all_timestamps_epoch)
        global_epoch_step = 60  # quantizing global timeline to minutes

        global_timestamps_epoch = list(range(min_global_epoch, max_global_epoch, global_epoch_step))
        global_timeline_len = len(global_timestamps_epoch)

        global_cpu = [0.0] * global_timeline_len
        global_mem = [0.0] * global_timeline_len
        global_disk_used = [0.0] * global_timeline_len
        global_disk_avl = [0.0] * global_timeline_len
        is_running = {timeline.node_name: [False] * global_timeline_len for timeline in timelines}

        for timeline in timelines:
            last_seen_global_idx = 0
            for local_idx, timestamp in enumerate(timeline.timestamps):
                epoch = timestamp.timestamp()
                global_idx = int((epoch - min_global_epoch) / global_epoch_step)
                is_running[timeline.node_name][global_idx] = True
                global_cpu[global_idx] += timeline.cpu[local_idx]
                global_mem[global_idx] += timeline.mem[local_idx]
                # cumulative data
                for global_idx_between_points in range(last_seen_global_idx, global_idx):
                    global_disk_used[global_idx_between_points] += timeline.disk_used[local_idx]
                    global_disk_avl[global_idx_between_points] += timeline.disk_avl[local_idx]
                last_seen_global_idx = global_idx

        # cumulative data have to go until the end!
        for global_idx_between_points in range(last_seen_global_idx, len(global_timestamps_epoch)):
            global_disk_used[global_idx_between_points] += global_disk_used[last_seen_global_idx - 1]
            global_disk_avl[global_idx_between_points] += global_disk_avl[last_seen_global_idx - 1]

        # uptime plot
        nodes_n = len(timelines)
        y_ticks = []
        y_tick_labels = []
        for node_i, (node_name, uptime_mask) in enumerate(is_running.items()):
            xs = [dt_e for i, dt_e in enumerate(global_timestamps_epoch) if uptime_mask[i]]
            y_ticks.append(nodes_n - node_i)
            y_tick_labels.append(node_name)
            ys = [nodes_n - node_i] * len(xs)  # nodes from top to bottom
            plt.scatter(xs, ys, marker="big")
        plot_width, _ = cls._get_plot_width_height()
        x_n = len(xs)
        x_tick_indices = [0, int(0.33 * x_n), int(0.66 * x_n), x_n - 1]
        x_ticks = [xs[idx] for idx in x_tick_indices]
        x_tick_labels = [datetime2str(datetime.fromtimestamp(xs[idx])) for idx in x_tick_indices]
        plt.plotsize(plot_width, nodes_n + (nodes_n - 1) + 3)
        plt.yticks(y_ticks, y_tick_labels)
        plt.xticks(x_ticks, x_tick_labels)
        click.secho("\nUptimes", bold=True)
        click.echo("Note: small apparent downtimes can be caused by temporary errors of system resources monitor")
        plt.show()

        global_timeline = SystemResourcesTimeline(
            node_name="Merged nodes data",
            timestamps=[datetime.fromtimestamp(ts) for ts in global_timestamps_epoch],
            ret=[timedelta(seconds=ts - min_global_epoch) for ts in global_timestamps_epoch],
            cpu=global_cpu,
            mem=global_mem,
            disk_used=global_disk_used,
            disk_avl=global_disk_avl,
        )
        global_timeline.display(absolute_x_axis=False, with_node_name=True)
