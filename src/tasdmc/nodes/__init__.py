import click

from .node_executor import node_executors_from_config


def _echo_ok():
    click.secho("OK", fg='green')


def _echo_fail():
    click.secho("FAIL", fg='red')


def check_all():
    click.echo("Checking nodes connectivity...", nl=False)
    failed_nodes = []
    for ex in node_executors_from_config():
        if not ex.check():
            failed_nodes.append(ex)
    if len(failed_nodes) > 0:
        _echo_fail()
        raise RuntimeError(
            f"Nodes check failed: "
            + ", ".join([str(ex) for ex in failed_nodes])
        )
    else:
        _echo_ok()


def run_all_dry():
    click.echo(f"Checking if nodes are ready to run their parts of the simulations...")
    for ex in node_executors_from_config():
        click.echo(f"{ex}: ", nl=False)
        try:
            ex.run_node(dry=True)
            _echo_ok()
        except Exception as e:
            _echo_fail()
            raise e


def run_all():
    click.echo(f"Running...")
    for ex in node_executors_from_config():
        click.echo(ex)
        ex.run_node()
