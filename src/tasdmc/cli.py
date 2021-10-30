"""Command line interface used by click package to create `tasdmc` executable"""

import click
from pathlib import Path

from tasdmc import config, fileio, system, pipeline, cleanup, extract_calibration
from tasdmc.progress import display as display_progress
from tasdmc.config.update_config import update_config


@click.group()
def cli():
    pass


# new run commands


def _run_config_option(param_name: str):
    return click.option(
        '-c',
        '--config',
        param_name,
        default='run.yaml',  # TODO: remove default, make this required option in prod
        show_default=True,
        type=click.Path(),
        help='run configuration .yaml file',
    )


def _run_standard_pipeline_in_background(continuing: bool):
    system.run_in_background(
        background_fn=lambda: pipeline.run_standard_pipeline(continuing),
        main_process_fn=lambda: click.echo(
            f"Running in the background. Use 'tasdmc ps {config.run_name()}' to check run status"
        ),
    )


@cli.command("run", help="Run simulation")
@_run_config_option('config_filename')
def run(config_filename):
    config.load(config_filename)
    config.validate()
    _run_standard_pipeline_in_background(continuing=False)


# esixting run commands


def _run_name_argument(param_name: str):

    def autocomplete(ctx, param, incomplete):
        return [run_name for run_name in fileio.get_all_run_names() if run_name.startswith(incomplete)]

    return click.argument(param_name, type=click.STRING, shell_complete=autocomplete)


def _load_config_by_run_name(name: str) -> bool:
    try:
        config.load(fileio.get_run_config_path(name))
        return True
    except ValueError as e:
        click.secho(str(e), fg='red')
        return False


@cli.command("abort", help="Abort execution of run NAME. This will kill all its processes immediately!")
@_run_name_argument('name')
def abort_run(name: str):
    if not _load_config_by_run_name(name):
        return
    click.secho(f"You are about to kill run '{name}'!\nIf you are sure, type its name again below:")
    run_name_confirmation = input('> ')
    if name == run_name_confirmation:
        system.abort_run(main_pid=fileio.get_saved_main_pid())


@cli.command("continue", help="Continue execution of aborted run NAME")
@_run_name_argument('name')
def continue_run(name: str):
    if not _load_config_by_run_name(name):
        return
    if system.process_alive(pid=fileio.get_saved_main_pid()):
        click.secho(f"Run already alive")
        return
    _run_standard_pipeline_in_background(continuing=True)


@cli.command("update-config", help="Update config of run NAME")
@_run_config_option('new_config_filename')
@_run_name_argument('name')
def update_config_in_run(name: str, new_config_filename: str):
    if not _load_config_by_run_name(name):
        return
    update_config(new_config_filename)


@cli.command("progress", help="Display progress for run NAME")
@_run_name_argument('name')
def run_progress(name: str):
    if not _load_config_by_run_name(name):
        return
    display_progress.print_pipelines_progress()


@cli.command("inputs", help="Display inputs for run NAME")
@_run_name_argument('name')
def run_inputs(name: str):
    if not _load_config_by_run_name(name):
        return
    click.echo(fileio.cards_gen_info_log().read_text())


@cli.command("ps", help="Display processes status and last debug messages from worker processes for run NAME")
@_run_name_argument('name')
@click.option("-n", "n_last_messages", default=1, help="Number of messages from worker processes to print")
def run_process_status(name: str, n_last_messages: int):
    if not _load_config_by_run_name(name):
        return
    main_pid = fileio.get_saved_main_pid()
    system.print_process_status(main_pid)
    display_progress.print_multiprocessing_debug(n_last_messages)


@cli.command(
    "_cleanup_failed_pipelines",
    help="Delete all files related to run NAME's pipelines currently marked as .failed; INTERNAL/EXPERIMENTAL COMMAND",
)
@_run_name_argument('name')
def cleanup_failed_pipelines(name: str):
    if not _load_config_by_run_name(name):
        return
    failed_pipeline_files = cleanup.get_failed_pipeline_files()
    if not failed_pipeline_files:
        click.echo("No failed pipelines found")
        return
    click.echo("Failed pipelines to be removed:\n" + "\n".join([f'\t{p}' for p in failed_pipeline_files]))
    click.echo("\nType 'yes' to confirm")
    confirmation = input('> ')
    if confirmation == 'yes':
        for fp in failed_pipeline_files:
            cleanup.delete_all_files_from_failed_pipeline(fp)


# other commands


@cli.command(
    "extract-calibration",
    help="Exctract calibration from raw per-day data",
)
@click.option(
    "-r",
    "--raw-data",
    "raw_data_dir",
    required=True,
    type=click.Path(),
    help='Directory containing raw calibration data (calib and const subfolders with .dst files',
)
@click.option(
    "-p",
    "--parallel",
    "parallel_threads",
    default=1,
    help='Number of threads to run in',
)
def extract_calibration_cmd(raw_data_dir, parallel_threads):
    extract_calibration.extract_calibration(Path(raw_data_dir), parallel_threads)
