import psutil
import setproctitle
import click

from typing import List, Optional


def set_process_title(title: str):
    setproctitle.setproctitle(title)


def _proc2str(p: psutil.Process) -> str:
    return f"{p.pid} ({p.name()})"


def process_alive(pid: int) -> bool:
    try:
        psutil.Process(pid)
        return True
    except psutil.NoSuchProcess:
        return False


def abort_run(main_pid: int):
    try:
        main_process = psutil.Process(main_pid)
    except psutil.NoSuchProcess:
        click.echo(
            "Main process has already been killed! "
            + "If you have killed it directly with 'kill <pid>' or Ctrl+C, you might need to "
            + "find and kill all the child processes manually..."
        )
        return
    child_processes = main_process.children(recursive=True)
    for p in [*child_processes, main_process]:
        try:
            p.terminate()
            click.echo(f"Killed process {_proc2str(p)}")
        except psutil.NoSuchProcess:
            click.echo("Process already killed")


def get_run_processes(main_pid: int) -> Optional[List[psutil.Process]]:
    try:
        main_process = psutil.Process(main_pid)
        return [main_process, *main_process.children(recursive=True)]
    except psutil.NoSuchProcess:
        return None


def print_process_status(main_pid: int):
    try:
        main_process = psutil.Process(main_pid)
        click.echo("Run is alive!")
    except psutil.NoSuchProcess:
        click.echo("Run is not active")
        return
    worker_process_ids = set()
    click.secho("tasdmc processes:", bold=True)
    for i, p in enumerate([main_process, *main_process.children()]):
        worker_process_ids.add(p.pid)
        click.echo(f"\t{i + 1}. {_proc2str(p)}")

    click.secho("\nC routine processes:", bold=True)
    i = 0
    for p in main_process.children(recursive=True):
        if p.pid not in worker_process_ids:
            click.echo(f"\t{i + 1}. {_proc2str(p)}")
            i += 1

    return True
