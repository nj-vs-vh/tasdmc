import click

from typing import List

from tasdmc import config, fileio
from tasdmc.utils import user_confirmation
from tasdmc.logs.display import PipelineProgress
from .node_executor import node_executors_from_config


def _echo_ok():
    click.secho("OK", fg='green')


def _echo_fail():
    click.secho("FAIL", fg='red')


def check_all():
    click.echo("Checking nodes connectivity... ")
    failed_nodes = []
    for ex in node_executors_from_config():
        if not ex.check():
            failed_nodes.append(ex)
    if len(failed_nodes) > 0:
        raise RuntimeError(f"Nodes check failed: " + ", ".join([str(ex) for ex in failed_nodes]))
    else:
        _echo_ok()


def run_all_dry():
    click.echo(f"Checking if nodes are ready to run their parts of the simulation...")
    for ex in node_executors_from_config():
        click.secho(f"{ex}: ", nl=False, bold=True)
        try:
            ex.run_simulation(dry=True)
            _echo_ok()
        except Exception as e:
            _echo_fail()
            raise e


def run_all():
    click.echo(f"Running...")
    for ex in node_executors_from_config():
        click.secho(ex, bold=True)
        ex.run_simulation()


def continue_all():
    click.echo(f"Continuing nodes...")
    failed_nodes = []
    for ex in node_executors_from_config():
        click.secho(f"{ex}: ", nl=False, bold=True)
        try:
            ex.continue_simulation()
            _echo_ok()
        except Exception as e:
            _echo_fail()
            click.echo(e)
            failed_nodes.append(ex)
    if len(failed_nodes) > 0:
        raise RuntimeError(f"Continuing nodes failed: " + ", ".join([str(ex) for ex in failed_nodes]))


def abort_all():
    click.echo(f"Aborting nodes...")
    for ex in node_executors_from_config():
        click.secho(f"\n{ex}", bold=True)
        ex.run(f"tasdmc abort {ex.node_run_name} --confirm", check_result=False, echo_streams=True)


def update_configs(hard: bool, validate_only: bool):
    click.echo(f"Checking node configs...")
    failed = []
    for ex in node_executors_from_config():
        click.secho(f"\n{ex}", bold=True)
        if not ex.update_config(dry=True):
            failed.append(ex)
    if len(failed) > 0:
        raise RuntimeError("Some nodes refused to update configs: " + ", ".join([str(ex) for ex in failed]))
    if not validate_only and (hard or user_confirmation("Apply?", yes="yes", default=False)):
        for ex in node_executors_from_config():
            ex.update_config()
        config.RunConfig.dump(fileio.saved_run_config_file())
        config.NodesConfig.dump(fileio.saved_nodes_config_file())


def collect_progress_data() -> List[PipelineProgress]:
    click.echo(f"Collecting progress data from nodes...")
    plps: List[PipelineProgress] = []
    for ex in node_executors_from_config():
        click.secho(f"{ex}: ", bold=True, nl=False)
        res = ex.run(f"tasdmc progress {ex.node_run_name} --dump-json")
        _echo_ok()
        plp = PipelineProgress.load(res.stdout)
        plp.node_name = str(ex)
        plps.append(plp)
    return plps


def print_statuses(n_last_messages: int, display_processes: bool):
    click.echo(f"Checking node runs statuses...")
    for ex in node_executors_from_config():
        click.secho(f"\n{ex}", bold=True)
        ex.run(
            f"tasdmc status {ex.node_run_name} -n {n_last_messages} {'-p' if display_processes else ''}",
            echo_streams=True,
        )


def print_inputs():
    click.echo(f"Checking node runs statuses...")
    for ex in node_executors_from_config():
        click.secho(f"\n{ex}", bold=True)
        ex.run(f"tasdmc inputs {ex.node_run_name}", echo_streams=True)
