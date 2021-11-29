import click

from .node_executor import node_executors_from_config


def check() -> bool:
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
