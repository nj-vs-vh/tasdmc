import sys
import click
from time import sleep
from pathlib import Path
import gdown
from gdown.cached_download import assert_md5sum

from tasdmc import config, pipeline, system, fileio, inspect, hard_cleanup, extract_calibration, nodes
from tasdmc.config.update import update_run_config
from tasdmc.logs import display as display_logs
from tasdmc.utils import user_confirmation_destructive

from .group import cli
from .options import run_config_option, nodes_config_option
from .utils import run_standard_pipeline_in_background, loading_run_by_name, error_catching


# new run commands


@cli.command("run-local", help="Run simulation locally on this machine")
@run_config_option('run_config_filename')
@error_catching
def local_run_cmd(run_config_filename: str):
    config.RunConfig.load(run_config_filename)
    fileio.prepare_run_dir()
    run_standard_pipeline_in_background()


@cli.command(
    "run-local-dry",
    help="Dry run: create simulation directory, validate config, "
    + "generate input files and then cleanup as if nothing happened",
)
@run_config_option('run_config_filename')
@error_catching
def local_run_cmd(run_config_filename: str):
    config.RunConfig.load(run_config_filename)
    fileio.prepare_run_dir()
    try:
        pipeline.run_standard_pipeline(dry=True)
    finally:
        fileio.remove_run_dir()


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


# existing run control commands


@cli.command("continue", help="Continue execution of aborted run NAME")
@loading_run_by_name
@error_catching
def continue_run_cmd():
    if config.is_local_run():
        if system.process_alive(pid=fileio.get_saved_main_pid()):
            click.secho(f"Run already alive")
            sys.exit(1)
        fileio.prepare_run_dir(continuing=True)
        run_standard_pipeline_in_background()
    else:
        nodes.check_all()
        nodes.continue_all()


@cli.command("abort", help="Abort execution of run NAME")
@loading_run_by_name
@error_catching
def abort_run_cmd():
    click.secho(f"You are about to kill run '{config.run_name()}'!")
    if user_confirmation_destructive(config.run_name()):
        system.abort_run(main_pid=fileio.get_saved_main_pid())
    else:
        click.echo("Not this time...")


@cli.command("config-update", help="Update configuration of run NAME")
@click.option("--hard", is_flag=True, default=False, help="Flag to update config without detailed inspection")
@run_config_option('new_config_filename')
@loading_run_by_name
@error_catching
def update_config_cmd(new_config_filename: str, hard: bool):
    update_run_config(new_config_filename, hard)


# monitoring commands


@cli.command("progress", help="Display progress for run NAME")
@click.option(
    "-f",
    "--follow",
    is_flag=True,
    default=False,
    help="Update progress bar each few seconds. Warning: clears terminal!",
)
@loading_run_by_name
@error_catching
def progress_cmd(follow: bool):
    if not follow:
        display_logs.print_pipelines_progress()
    else:
        while True:
            click.clear()
            display_logs.print_pipelines_progress()
            sleep(3)


@cli.command("ps", help="Display processes status and last debug messages from worker processes for run NAME")
@click.option("-n", "n_last_messages", default=1, help="Number of messages from worker processes to print")
@loading_run_by_name
@error_catching
def process_status_cmd(n_last_messages: int):
    system.print_process_status(fileio.get_saved_main_pid())
    if n_last_messages:
        display_logs.print_multiprocessing_log(n_last_messages)


@cli.command("resources", help="Display system resources utilization for run NAME")
@click.option(
    "-t",
    "--absolute-datetime",
    "absolute_datetime",
    default=False,
    is_flag=True,
    help="If set to True, X axis on plots represent absolute datetimes in UTC; otherwise Run Evaluation Time is used",
)
@click.option(
    "-p",
    "--include-previous",
    "include_previous_runs",
    default=False,
    is_flag=True,
    help="If set to True, all previous run execution logs will be merged into one timeline",
)
@loading_run_by_name
@error_catching
def system_resources_cmd(include_previous_runs: bool, absolute_datetime: bool):
    display_logs.print_system_monitoring(
        include_previous_runs=include_previous_runs, evaluation_time_as_x=(not absolute_datetime)
    )


@cli.command("inputs", help="Display inputs for run NAME")
@loading_run_by_name
@error_catching
def inputs_cmd():
    click.echo(fileio.cards_gen_info_log().read_text())


# deep inspection commands


@cli.command("fix-failed", help="Fix failed pipelines")
@click.option("--hard", is_flag=True, default=False, help="If specified, removes all failed pipeline files entirely")
@loading_run_by_name
@error_catching
def fix_failed_pipelines_cmd(hard: bool):
    failed_pipeline_ids = fileio.get_failed_pipeline_ids()
    if not failed_pipeline_ids:
        click.echo("No failed pipelines to fix")
        return
    if hard:
        hard_cleanup.delete_all_pipelines(failed_pipeline_ids)
    else:
        inspect.inspect_and_fix_failed(failed_pipeline_ids)


@cli.command("inspect", help="Inspect pipelines step-by-step")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Print verbose information about steps")
@click.option("-p", "--page", "pagesize", default=0, help="Page size or 0 for no pagination (default)")
@click.option("-f", "--failed", is_flag=True, default=False, help="Inspect only failed pipelines")
@loading_run_by_name
@error_catching
def inspect_cmd(pagesize: int, verbose: bool, failed: bool):
    pipeline_ids = fileio.get_failed_pipeline_ids() if failed else fileio.get_all_pipeline_ids()
    inspect.inspect_pipelines(pipeline_ids, page_size=pagesize, verbose=verbose, fix=False)


# misc commands


@cli.command(
    "extract-calibration",
    help="Exctract calibration from raw per-day data",
)
@click.option(
    "-r",
    "--raw-data",
    "raw_data_dir",
    required=True,
    type=click.Path(exists=True, resolve_path=True),
    help='Directory containing raw calibration data (calib and const subfolders with .dst files',
)
@click.option(
    "-p",
    "--parallel",
    "parallel_threads",
    type=click.INT,
    default=1,
    help='Number of threads to run in',
)
@error_catching
def extract_calibration_cmd(raw_data_dir: str, parallel_threads: int):
    extract_calibration.extract_calibration(Path(raw_data_dir), parallel_threads)


@cli.command("download-data-files", help="Download data files necessary for the simulation (total of ~350 Mb)")
@error_catching
def download_data_files_cmd():
    for data_file, gdrive_id, expected_md5 in (
        (fileio.DataFiles.sdgeant, '1ZTSrrAg2T8bvIDhPuh2ruVShmubwvTWG', '0cebc42f86e227e2fb2397dd46d7d981'),
        (fileio.DataFiles.atmos, '1qZfUNXAyqVg5HwH9BYUGVQ-UDsTwl4FQ', '254c7999be0a48bd65e4bc8cbea4867f'),
    ):
        if not data_file.exists():
            data_file.parent.mkdir(parents=True, exist_ok=True)
            gdown.download(id=gdrive_id, output=str(data_file))
        assert_md5sum(data_file, expected_md5)


@cli.command("list", help="List existing runs")
@error_catching
def list_cmd():
    click.echo('\n'.join(fileio.get_all_run_names()))
