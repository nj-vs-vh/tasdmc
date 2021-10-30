"""Command line interface used by click package to create `tasdmc` executable"""

import click
from pathlib import Path

from tasdmc import config, fileio, system, pipeline, cleanup, extract_calibration
from tasdmc.progress import display as display_progress


@click.group()
def cli():
    pass


# new run commands


def _run_config_option(param_name: str):
    return click.option(
        '-c',
        '--config',
        param_name,
        default='run.yaml',
        show_default=True,
        type=click.Path(),
        help='run configuration .yaml file',
    )


@cli.command("run", help="Run simulation")
@_run_config_option('config_filename')
@click.option("--bg/--fg", default=True, help="Run in background and detach from current terminal")
def run(config_filename, bg):
    config.load(config_filename)
    config.validate()
    if bg:
        system.run_in_background(
            pipeline.run_standard_pipeline,
            main_process_fn=lambda: click.echo(
                f"Running in the background. Use 'tasdmc ps {config.run_name()}' to check run status"
            ),
        )
    else:
        pipeline.run_standard_pipeline()


# esixting run commands


def _autocomplete_run_name(ctx, param, incomplete):
    return [run_name for run_name in fileio.get_all_run_names() if run_name.startswith(incomplete)]


def _run_name_argument(param_name: str):
    return click.argument(param_name, type=click.STRING, shell_complete=_autocomplete_run_name)


@cli.command("progress", help="Display progress for run NAME")
@_run_name_argument('name')
def progress(name: str):
    config.load(fileio.get_run_config_path(name))
    display_progress.print_pipelines_progress()


@cli.command("inputs", help="Display inputs for run NAME")
@_run_name_argument('name')
def inputs(name: str):
    config.load(fileio.get_run_config_path(name))
    click.echo(fileio.cards_gen_info_log().read_text())


@cli.command("ps", help="Display processes status and print last debug messages from worker processes for run NAME")
@_run_name_argument('name')
@click.option("-n", "n_last_messages", default=1, help="Number of messages from worker processes to print")
def ps(name: str, n_last_messages: int):
    config.load(fileio.get_run_config_path(name))
    main_process_id = fileio.get_saved_main_process_id()
    system.print_process_status(main_process_id)
    display_progress.print_multiprocessing_debug(n_last_messages)


@cli.command("abort", help="Abort execution of run specified by NAME. This will kill all processes in specified run!")
@_run_name_argument('name')
def abort(name: str):
    config.load(fileio.get_run_config_path(name))
    main_run_process_id = fileio.get_saved_main_process_id()
    click.secho(f"You are about to kill all processes in run '{name}'!\nIf you are sure, type its name again below:")
    run_name_confirmation = input('> ')
    if name == run_name_confirmation:
        system.kill_all_run_processes_by_main_process_id(main_run_process_id)


@cli.command(
    "_cleanup_failed_pipelines",
    help="Delete all files related to run NAME's pipelines currently marked as .failed; INTERNAL/EXPERIMENTAL COMMAND",
)
@_run_name_argument('name')
def cleanup_failed_pipelines(name: str):
    config.load(fileio.get_run_config_path(name))
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
