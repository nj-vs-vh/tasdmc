import time
import psutil
import os
import sys

from tasdmc import config, logs, fileio
from .resources import available_disk_space, directory_size
from .processes import set_process_title, get_run_processes
from .utils import bytes2Gb


def run_system_monitor():
    set_process_title("tasdmc system monitor")
    interval = config.get_key("resources.monitor_interval", default=60)
    if interval is None or interval == 0:
        return
    interval = float(interval)

    while True:
        time_before_measurement = time.time()

        processes = get_run_processes(fileio.get_saved_main_pid())
        if processes is None:
            sys.exit(0)
        for _ in range(5):  # trying several times
            try:
                running_processes = [
                    p for p in processes if p.status() == psutil.STATUS_RUNNING and p.pid != os.getpid()
                ]
                if running_processes:
                    cpu_percents = [p.cpu_percent(0.3) for p in running_processes]
                    #                    same as top‘s RES column
                    memory_used = [bytes2Gb(p.memory_info().rss) for p in running_processes]
                    logs.system_resources_info(
                        "CPU "
                        + " ".join(f"{cp:.3f}" for cp in cpu_percents)
                        + " MEM "
                        + " ".join(f"{m:.3f}" for m in memory_used)
                        + f" DISK {directory_size(fileio.run_dir()):.3f}/{available_disk_space(fileio.run_dir()):.3f}"
                    )
                    break
            except Exception:
                pass

        time_after_measurement = time.time()
        time.sleep(max(1, interval - (time_after_measurement - time_before_measurement)))
