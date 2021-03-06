import psutil
import setproctitle
import click
import signal
from itertools import chain

from typing import List, Optional

from tasdmc import config, logs


def set_process_title(title: str):
    setproctitle.setproctitle(title)


def _proc2str(p: psutil.Process) -> str:
    try:
        return f"{p.pid} ({p.name()})"
    except psutil.NoSuchProcess:
        return f"{p.pid} was short-lived and died until displayed"


def is_alive(pid: int) -> bool:
    try:
        psutil.Process(pid)
        return True
    except psutil.NoSuchProcess:
        return False


def kill_process(pid: int):
    try:
        p = psutil.Process(pid)
        p.terminate()
    except psutil.NoSuchProcess:
        pass


def abort_run_processes(main_pid: int, safe: bool):
    try:
        main_process = psutil.Process(main_pid)
    except psutil.NoSuchProcess:
        click.echo(
            "Main process has already been killed! "
            + "If you have killed it directly with 'kill <pid>' or Ctrl+C, you might need to "
            + "find and kill all the child processes manually..."
        )
        return
    # on hard cleanup, core layer programs must also be terminated;
    # on soft cleanup only python processes receive SIGUSR1, it is catched and config.Ephemeral.safe_abort_in_progress
    # flag is set to True
    child_processes = main_process.children(recursive=(not safe))
    for p in [*child_processes, main_process]:
        try:
            p.send_signal(signal.SIGTERM if not safe else signal.SIGUSR1)
            action_str = "Killed" if not safe else "Sent safe abort signal to"
            click.echo(f"{action_str} process {_proc2str(p)}")
        except psutil.NoSuchProcess:
            click.echo(f"Process already killed: {_proc2str(p)}")


def setup_safe_abort_signal_listener():
    def handler(*args):
        logs.multiprocessing_info(
            "Safe abort signal received, running step will be completed and all later steps cancelled"
        )
        config.Ephemeral.safe_abort_in_progress = True

    signal.signal(signal.SIGUSR1, handler)


def _get_grandchildren_processes(p: psutil.Process) -> List[psutil.Process]:
    return list(chain.from_iterable(child.children() for child in p.children()))


def get_core_layer_run_processes(main_pid: int) -> Optional[List[psutil.Process]]:
    try:
        main_process = psutil.Process(main_pid)
        return _get_grandchildren_processes(main_process)
    except psutil.NoSuchProcess:
        return None


def print_run_processes_status(main_pid: int, display_processes: bool):
    try:
        main_process = psutil.Process(main_pid)
        click.echo("Run is alive!")
    except psutil.NoSuchProcess:
        click.echo("Run is dead!")
        return

    if display_processes:
        click.secho("tasdmc processes:", bold=True)
        for i, p in enumerate([main_process, *main_process.children()]):
            click.echo(f"\t{i + 1}. {_proc2str(p)}")

        click.secho("\nCore layer processes:", bold=True)
        for i, p in enumerate(_get_grandchildren_processes(main_process)):
            click.echo(f"\t{i + 1}. {_proc2str(p)}")
