import sys
import click

from tasdmc import config, system, fileio, nodes, fork
from tasdmc.config.update import update_run_config
from tasdmc.utils import user_confirmation_destructive

from ..group import cli
from ..options import run_config_option, nodes_config_option
from ..utils import run_standard_pipeline_in_background, loading_run_by_name, error_catching


@cli.command("continue", help="Continue execution of aborted RUN_NAME")
@click.option(
    "--rerun-step-on-input-hash-mismatch",
    is_flag=True,
    default=False,
    help="By default on input hash mismatch step is marked as failed. If the mismatch is due to you changing run"
    + "config 'on the fly', specify this option and steps with mismatching input hashes will be rerun"
)
@click.option(
    "--disable-input-hash-checks",
    is_flag=True,
    default=False,
    help="Option to completely disable input hash checking (a mechanism to prevent pipeline desync). "
    + "If specified, hashes of input files will still be calculated and saved, hence subsequent 'continue's "
    + "will see pipelines as forcibly synced. Use this if you have a problem with hashes not"
    + "related to configuration change, but due to some technical issue."
)
@loading_run_by_name
@error_catching
def continue_run_cmd(rerun_step_on_input_hash_mismatch: bool, disable_input_hash_checks: bool):
    if rerun_step_on_input_hash_mismatch and disable_input_hash_checks:
        click.echo("--rerun-step-on-input-hash-mismatch and --disable-input-hash-checks options can't be used together")
        sys.exit(1)
    if config.is_local_run():
        config.Ephemeral.rerun_step_on_input_hash_mismatch = rerun_step_on_input_hash_mismatch
        config.Ephemeral.disable_input_hash_checks = disable_input_hash_checks
        saved_main_pid = fileio.get_saved_main_pid()
        if saved_main_pid is not None and system.process_alive(saved_main_pid):
            click.secho(f"Run already alive")
            sys.exit(1)
        fileio.prepare_run_dir(continuing=True)
        run_standard_pipeline_in_background()
    else:
        nodes.check_all()
        nodes.continue_all(rerun_step_on_input_hash_mismatch, disable_input_hash_checks)


@cli.command("abort", help="Abort execution of RUN_NAME")
@click.option("--confirm", is_flag=True, default=False, help="Disable confirmation prompt")
@loading_run_by_name
@error_catching
def abort_run_cmd(confirm: bool):
    if config.is_distributed_run():
        nodes.check_all()
    if not confirm:
        click.secho(f"You are about to kill run '{config.run_name()}'!")
    if confirm or user_confirmation_destructive(config.run_name()):
        if config.is_local_run():
            saved_main_pid = fileio.get_saved_main_pid()
            if saved_main_pid is not None:
                system.abort_run(saved_main_pid)
            else:
                click.echo("No saved main pid found for the run")
        else:
            nodes.abort_all()
    else:
        click.echo("Not this time...")


@cli.command(
    "fork",
    help="Create a new run by forking RUN_NAME at the specified pipeline step; "
    + "This command does not copy any actual data but creates symlinks instead"
)
@click.option(
    "--after", "-a", "after",
    required=True,
    help="A stage at which fork happens; currently may only be 'corsika' to fork after CORSIKA simulation step"
)
@click.option("--fork-name", "-n", "fork_name", required=True, help="Name of the forked run")
@loading_run_by_name
@error_catching
def fork_cmd(fork_name: str, after: str):
    if config.is_distributed_run():
        click.echo("Forking is currently available only for local runs")
        return
    fork.fork_run(fork_name, after)
    click.echo(f"Use 'tasdmc continue {fork_name}' to start forked simulation")


@cli.command("update-config", help="Update configuration of RUN_NAME")
@click.option("--hard", is_flag=True, default=False, help="Flag to update config without detailed inspection")
@click.option(
    "--validate-only", is_flag=True, default=False, help="Flag to only check updated config and report if it's valid"
)
@run_config_option('new_run_config_filename', optional=True)
@nodes_config_option('new_nodes_config_filename', optional=True)
@loading_run_by_name
@error_catching
def update_config_cmd(new_run_config_filename: str, new_nodes_config_filename: str, hard: bool, validate_only: bool):
    if config.is_local_run():
        if new_run_config_filename is None:
            raise ValueError("-r (new run config) option must be specified")
        click.echo(f"Updating run config with values from {new_run_config_filename}")
        if new_nodes_config_filename is not None:
            click.echo("-n option ignored for local run")

        update_run_config(new_run_config_filename, hard, validate_only)
    else:
        if new_run_config_filename is None and new_nodes_config_filename is None:
            raise ValueError("At least one of -r (new run config) and -n (new nodes config) options must be specified")
        nodes.check_all()

        if new_run_config_filename is not None:
            click.echo(f"Updating run config with values from {new_run_config_filename}")
            config.RunConfig.load(new_run_config_filename)
        if new_nodes_config_filename is not None:
            click.echo(f"Updating nodes config with values from {new_nodes_config_filename}")
            config.NodesConfig.load(new_nodes_config_filename)

        nodes.update_configs(hard, validate_only)
