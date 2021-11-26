import click

from .node_executor import node_executors_from_config


def check() -> bool:
    click.echo("Checking nodes...")
    disconnected_nodes = []
    for ex in node_executors_from_config():
        if not ex.check():
            disconnected_nodes.append(ex)
    if len(disconnected_nodes) > 0:
        raise RuntimeError(
            f"Nodes check failed: "
            + ", ".join([str(ex) for ex in disconnected_nodes])
        )
    else:
        click.secho("OK", fg='green')
