import click

from tasdmc import config, pipeline, fileio, nodes

from tasdmc.cli.group import cli
from ..options import run_config_option, nodes_config_option
from ..utils import run_standard_pipeline_in_background, error_catching


@cli.command("run-local", help="Run simulation on this machine")
@run_config_option('run_config_filename')
@click.option(
    "--dry",
    is_flag=True,
    default=False,
    help="Check that simulation is runnable but do not run it",
)
@click.option(
    "--foreground",
    is_flag=True,
    default=False,
    help="Assume that you will background & disown the program yourself",
)
@error_catching
def local_run_cmd(run_config_filename: str, dry: bool, foreground: bool):
    config.RunConfig.load(run_config_filename)
    fileio.prepare_run_dir()
    if dry:
        try:
            pipeline.run_simulation(dry=True)
        finally:
            fileio.remove_run_dir()
    else:
        if foreground:
            pipeline.run_simulation()
        else:
            run_standard_pipeline_in_background()


@cli.command("run-distributed", help="Run simulation distributed across several machines (nodes)")
@click.option(
    "--dry",
    is_flag=True,
    default=False,
    help="Check that all nodes are connectable and capable of running the simulation",
)
@run_config_option('run_config_filename')
@nodes_config_option('nodes_config_filename')
@error_catching
def distributed_run_cmd(run_config_filename: str, nodes_config_filename: str, dry: bool):
    config.RunConfig.load(run_config_filename)
    config.NodesConfig.load(nodes_config_filename)
    nodes.check_all()
    nodes.run_all_dry()
    if dry:
        return
    fileio.prepare_run_dir()
    nodes.run_all()
