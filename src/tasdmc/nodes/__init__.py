import click

from .node_executor import node_executors_from_config


def _echo_ok():
    click.secho("OK", fg='green')


def _echo_fail():
    click.secho("FAIL", fg='red')


def check_all():
    msg = "Checking nodes connectivity... "
    click.echo(f"{msg}\r", nl=False)
    failed_nodes = []
    for ex in node_executors_from_config():
        if not ex.check():
            failed_nodes.append(ex)
    if len(failed_nodes) > 0:
        raise RuntimeError(
            f"Nodes check failed: "
            + ", ".join([str(ex) for ex in failed_nodes])
        )
    else:
        click.echo(msg, nl=False)
        _echo_ok()


def run_all_dry():
    click.echo(f"Checking if nodes are ready to run their parts of the simulation...")
    for ex in node_executors_from_config():
        click.echo(f"\t{ex}: ", nl=False)
        try:
            ex.run_simulation(dry=True)
            _echo_ok()
        except Exception as e:
            _echo_fail()
            raise e


def run_all():
    click.echo(f"Running...")
    for ex in node_executors_from_config():
        click.echo(ex)
        ex.run_simulation()


def continue_all():
    click.echo(f"Continuing nodes...")
    failed_nodes = []
    for ex in node_executors_from_config():
        click.echo(ex)
        try:
            ex.continue_simulation()
            _echo_ok()
        except Exception as e:
            _echo_fail()
            click.echo(f"{ex}: {e}")
            failed_nodes.append(ex)
    if len(failed_nodes) > 0:
        raise RuntimeError(
            f"Continuing nodes failed: "
            + ", ".join([str(ex) for ex in failed_nodes])
        )
