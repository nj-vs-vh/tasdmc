import click

from .node_executor import node_executors_from_config


def check_connectivity() -> bool:
    click.echo("Checking nodes connectivity: ", nl=False)
    disconnected_nodes = []
    for ex in node_executors_from_config():
        if ex.check_connectivity():
            click.secho("✓", fg='green', nl=False)
        else:
            click.secho("×", fg='red', nl=False)
            disconnected_nodes.append(ex)
    click.echo()
    if len(disconnected_nodes) > 0:
        raise RuntimeError(
            f"Failed to connect to {len(disconnected_nodes)} nodes: "
            + ", ".join([str(ex) for ex in disconnected_nodes])
        )
