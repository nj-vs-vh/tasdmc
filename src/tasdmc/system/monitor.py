from __future__ import annotations

import time
import psutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from typing import Optional

from tasdmc import config, logs, fileio
from .resources import available_disk_space, directory_size
from .processes import set_process_title, get_core_layer_run_processes
from .utils import bytes2Gb, bytes2Mb


@dataclass(frozen=True)
class ProcessStats:
    cpu: float
    mem: float
    disk_read: float  # Mb/sec
    disk_write: float  # Mb/sec

    @classmethod
    def measure(cls, p: psutil.Process) -> Optional[ProcessStats]:
        try:
            io_ctrs_start = p.io_counters()
            time.sleep(1.0)
            io_ctrs_end = p.io_counters()
            return ProcessStats(
                cpu=p.cpu_percent(interval=0.5),
                # vms, aka “Virtual Memory Size”, this is the total amount of virtual memory
                # used by the process. On UNIX it matches “top“‘s VIRT column.
                mem=bytes2Gb(p.memory_info().vms),
                disk_read=bytes2Mb(io_ctrs_end.read_bytes - io_ctrs_start.read_bytes),
                disk_write=bytes2Mb(io_ctrs_end.write_bytes - io_ctrs_start.write_bytes),
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
            logs.multiprocessing_info("Exiting system monitor: seems like the main run process is dead")
            return

        # measuring all processes simultaneously in their own respective threads
        with ThreadPoolExecutor(max_workers=len(core_layer_processes)) as executor:
            maybe_stats = executor.map(ProcessStats.measure, core_layer_processes)
            stats = [s for s in maybe_stats if s is not None]

        if stats:
            disk_used = directory_size(fileio.run_dir())
            disk_available = available_disk_space(fileio.run_dir())
            logs.system_resources_info(
                "CPU "
                + " ".join(f"{s.cpu:.1f}" for s in stats)
                + " MEM "
                + " ".join(f"{s.mem:.3f}" for s in stats)
                + f" DISK {disk_used:.3f}/{disk_available:.3f}"
                + " DISKR "
                + " ".join(f"{s.disk_read:2f}" for s in stats)
                + " DISKW "
                + " ".join(f"{s.disk_write:2f}" for s in stats)
            )
        else:
            logs.multiprocessing_info("System monitor was unable to collect any core layer process data")
