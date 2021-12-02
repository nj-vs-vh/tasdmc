import click

from .node_executor import node_executors_from_config


def check_all():
    click.echo("Checking nodes...")
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
        click.secho("OK", fg='green')


def run_all_dry():
    click.echo(f"Checking if nodes are ready to run...")
    for ex in node_executors_from_config():
        click.echo(f"{ex}: ", nl=False)
        try:
            ex.run_node(dry=True)
            click.secho("OK", fg="green")
        except Exception as e:
            click.secho("FAIL", fg="red")
            raise e


def run_all():
    click.echo(f"Running nodes...")
    for ex in node_executors_from_config():
        ex.run_node()
