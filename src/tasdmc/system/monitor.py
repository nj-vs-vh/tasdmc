import time
import psutil
import os
from dataclasses import dataclass

from typing import Dict

from tasdmc import config, logs, fileio
from .resources import available_disk_space, directory_size
from .processes import set_process_title, get_core_layer_run_processes
from .utils import bytes2Gb


@dataclass
class ProcessStats:
    cpu: int
    mem: int


def run_system_monitor():
    set_process_title("tasdmc system monitor")
    logs.multiprocessing_info("Running system monitor")
    interval = config.get_key("resources.monitor_interval", default=60)
    if interval is None or interval == 0:
        return
    interval = float(interval)

    saved_main_pid = fileio.get_saved_main_pid()
    if saved_main_pid is None:
        logs.multiprocessing_info("Error in system monitor: main process pid not found")
        return
    while True:  # main measurement cycle
        time.sleep(interval)

        stats_by_pid: Dict[int, ProcessStats] = dict()
        for _ in range(5):
            core_layer_processes = get_core_layer_run_processes(saved_main_pid)
            if core_layer_processes is None:
                logs.multiprocessing_info("Exiting system monitor: seems like main run process has died")
                return
            # pids that were active on last iteration but not anymore -- dropping them
            obsolete_pids = set(stats_by_pid.keys()) - {p.pid for p in core_layer_processes}
            if stats_by_pid and not obsolete_pids:
                break  # yay, no new processes spawned while we collected data from previous iteration
            for pid in obsolete_pids:
                stats_by_pid.pop(pid)
            for p in core_layer_processes:
                try:
                    if p.pid not in stats_by_pid:
                        with p.oneshot():
                            stats_by_pid[p.pid] = ProcessStats(
                                cpu=p.cpu_percent(interval=0.3),
                                # vms, aka “Virtual Memory Size”, this is the total amount of virtual memory
                                # used by the process. On UNIX it matches “top“‘s VIRT column.
                                mem=bytes2Gb(p.memory_info().vms),
                            )
                except Exception:
                    # happens when process has exited while we were collecting other processes' data
                    # it's ok, we have several iterations for that!
                    pass
        else:
            logs.multiprocessing_info(
                "Warning! System monitor was unable to collect adequate metrics for run processes"
            )

        cpu_percents = [s.cpu for s in stats_by_pid.values()]
        mem_usage = [s.mem for s in stats_by_pid.values()]
        disk_used = directory_size(fileio.run_dir())
        disk_available = available_disk_space(fileio.run_dir())
        logs.system_resources_info(
            "CPU "
            + " ".join(f"{cp:.3f}" for cp in cpu_percents)
            + " MEM "
            + " ".join(f"{m:.3f}" for m in mem_usage)
            + f" DISK {disk_used:.3f}/{disk_available:.3f}"
        )
