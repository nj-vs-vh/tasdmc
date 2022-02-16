from __future__ import annotations

import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from typing import Dict, Optional, List

from tasdmc import config, logs, fileio
from .resources import available_disk_space, directory_size
from .processes import set_process_title, get_core_layer_run_processes
from .utils import bytes2Gb


@dataclass(frozen=True)
class ProcessStats:
    cpu: int
    mem: int

    @classmethod
    def measure(cls, p: psutil.Process) -> Optional[ProcessStats]:
        try:
            with p.oneshot():
                return ProcessStats(
                    cpu=p.cpu_percent(interval=0.3),
                    # vms, aka “Virtual Memory Size”, this is the total amount of virtual memory
                    # used by the process. On UNIX it matches “top“‘s VIRT column.
                    mem=bytes2Gb(p.memory_info().vms),
                )
        except Exception:
            return None


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

        core_layer_processes = get_core_layer_run_processes(saved_main_pid)
        if core_layer_processes is None:
            logs.multiprocessing_info("Exiting system monitor: seems like main run process has died")
            return

        # measuring all processes simultaneously in their own respective threads
        with ThreadPoolExecutor(max_workers=len(core_layer_processes)) as executor:
            futures = executor.map(ProcessStats.measure, core_layer_processes)
            future_results: List[Optional[ProcessStats]] = [f.result() for f in as_completed(futures)]
            stats = [fr for fr in future_results if fr is not None]

        if stats:
            cpu_percents = [ps.cpu for ps in stats]
            mem_usage = [ps.mem for ps in stats]
            disk_used = directory_size(fileio.run_dir())
            disk_available = available_disk_space(fileio.run_dir())
            logs.system_resources_info(
                "CPU "
                + " ".join(f"{cp:.3f}" for cp in cpu_percents)
                + " MEM "
                + " ".join(f"{m:.3f}" for m in mem_usage)
                + f" DISK {disk_used:.3f}/{disk_available:.3f}"
            )
        else:
            logs.multiprocessing_info("System monitor was unable to collect any core layer process data")
