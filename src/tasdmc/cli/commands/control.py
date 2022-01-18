import sys
import click
import shutil

from tasdmc import config, system, fileio, nodes, pipeline
from tasdmc.config.update import update_run_config
from tasdmc.utils import user_confirmation_destructive

from ..group import cli
from ..options import run_config_option, nodes_config_option
from ..utils import run_standard_pipeline_in_background, loading_run_by_name, error_catching


@cli.command("continue", help="Continue execution of aborted RUN_NAME")
@loading_run_by_name
@error_catching
def continue_run_cmd():
    if config.is_local_run():
        saved_main_pid = fileio.get_saved_main_pid()
        if saved_main_pid is not None and system.process_alive(saved_main_pid):
            click.secho(f"Run already alive")
            sys.exit(1)
        fileio.prepare_run_dir(continuing=True)
        run_standard_pipeline_in_background()
    else:
        nodes.check_all()
        nodes.continue_all()


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
            nodes.abort_all()
    else:
        click.echo("Not this time...")


@cli.command(
    "fork",
    help="Create a new run by forking RUN_NAME at the specified pipeline step; "
    + "This command does not copy any data but creates symlinks, forked run can potentially overwrite "
    + "files in the parent run, so use it with care!"
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
        click.echo("Sorry, fork is currently available only for local runs")
        return
    # TODO: manually listing directories here is bad, should infer them from step sequence and their i/o Files
    symlinked_dir_getters = [
        fileio.corsika_input_files_dir,
        fileio.corsika_output_files_dir,
    ]
    if after == 'corsika':
        pass
        # for later fork points dir_getters_to_symlink list should be extended
    else:
        raise ValueError("--after currently may be only 'corsika'")
    symlink_target_dirs = [dg() for dg in symlinked_dir_getters]
    old_input_hashes_dir = fileio.input_hashes_dir()
    config.RunConfig.loaded().update_name(fork_name)
    fileio.prepare_run_dir(create_only=True)
    # after config is updated dir getters will return new run's directories
    # but first we need to clear their caches
    [dg.cache_clear() for dg in symlinked_dir_getters]
    symlink_dirs = [dg() for dg in symlinked_dir_getters]
    for symlink_dir, symlink_target_dir in zip(symlink_dirs, symlink_target_dirs):
        click.echo(
            f"Creating symlink {symlink_dir.relative_to(config.Global.runs_dir)} -> "
            + f"{symlink_target_dir.relative_to(config.Global.runs_dir)}"
        )
        symlink_dir.symlink_to(symlink_target_dir, target_is_directory=True)
    fileio.prepare_run_dir(continuing=True)  # creating all the other dirs, copying configs, etc
    click.echo("Copying input hashes to the forked run")
    fileio.input_hashes_dir.cache_clear()
    for input_hash_file in old_input_hashes_dir.iterdir():
        shutil.copy(input_hash_file, fileio.input_hashes_dir() / input_hash_file.name)
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
