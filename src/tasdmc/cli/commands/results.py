from email.policy import default
import click
from pathlib import Path
import tarfile
import sys

from tasdmc import config, nodes, fileio

from tasdmc.utils import user_confirmation
from tasdmc import __version__
from tasdmc.cli.group import cli
from tasdmc.cli.utils import error_catching, loading_run_by_name


@cli.command(
    "archive-results",
    help="Archive <run-dir>/final directory into .tar.gz archive for export"
)
@click.option(
    "-o", "--output", required=True, type=click.Path(writable=True, resolve_path=True), help="Output tar path"
)
@loading_run_by_name
@error_catching
def archive_results(output: str):
    final_dir = fileio.final_dir()
    if not final_dir.exists():
        click.echo(f"{final_dir} does not exist, aborting")
        sys.exit(1)
    final_dir_files = list(final_dir.iterdir())
    if not len(final_dir_files) > 0:
        click.echo(f"{final_dir} is empty, aborting")
        sys.exit(1)
    
    in_archive_final_dir_name = "results"
    in_archive_config_dir_name = "config"
    with tarfile.open(output, "w:gz") as tar:
        for f in final_dir_files:
            tar.add(f, arcname=f"{in_archive_final_dir_name}/{f.name}")
        tar.add(fileio.saved_run_config_file(), arcname=f"{in_archive_config_dir_name}/run.yaml")
        if config.is_distributed_run():
            tar.add(fileio.saved_nodes_config_file(), arcname=f"{in_archive_config_dir_name}/nodes.yaml")


# @cli.command(
#     "collect-results",
#     help="Collect simulation results from distributed run nodes"
# )
# @loading_run_by_name
# def update_nodes():
#     if not config.is_distributed_run():
#         click.echo("Command is only available for distributed runs")
#     nodes.update_tasdmc_on_nodes()
