"""Command line interface used by click package to create `tasdmc` executable"""

try:
    import click
    from pathlib import Path
    import gdown
    from gdown.cached_download import assert_md5sum
    from time import sleep

    from tasdmc import __version__
    from tasdmc import config, fileio, system, pipeline, inspect, extract_calibration, hard_cleanup
    from tasdmc.logs import display as display_logs
    from tasdmc.config.update import update_config
    from tasdmc.utils import user_confirmation, user_confirmation_destructive
except ModuleNotFoundError:
    print("'tasdmc' was not installed properly: some dependencies are missing")
    import sys

    sys.exit(1)


@click.group()
@click.version_option(__version__)
def cli():
    pass


# new run commands


def _run_config_option(param_name: str):
    return click.option(
        '-c',
        '--config',
        param_name,
        type=click.Path(),
        help='configuration yaml file, see examples/run.yaml',
    )


def _run_standard_pipeline_in_background(continuing: bool):
    system.run_in_background(pipeline.run_standard_pipeline, continuing)
    click.echo(f"Running in the background. Use 'tasdmc ps {config.run_name()}' to check run status")


@cli.command("run", help="Run simulation")
@_run_config_option('config_filename')
def run(config_filename):
    config.RunConfig.load(config_filename)
    _run_standard_pipeline_in_background(continuing=False)


# esixting run commands


def _run_name_argument(param_name: str):
    def autocomplete(ctx, param, incomplete):
        return [run_name for run_name in fileio.get_all_run_names() if run_name.startswith(incomplete)]

    return click.argument(param_name, type=click.STRING, default="", shell_complete=autocomplete)


def _load_config_by_run_name(name: str) -> bool:
    run_config_path = None
    try:
        assert len(name), "No run name specified"
        run_config_path = fileio.get_run_config_path(name)
    except (AssertionError, ValueError) as exc:
        all_run_names = fileio.get_all_run_names()
        click.echo(f"{exc}, following runs exist:\n" + "\n".join([f"\t{r}" for r in all_run_names]))
        matching_run_names = [rn for rn in all_run_names if rn.startswith(name)]
        if len(matching_run_names) == 1:
            single_matching_run_name = matching_run_names[0]
            if user_confirmation(f"Did you mean '{single_matching_run_name}?'", yes='yes', no='no', default=True):
                click.echo()
                run_config_path = fileio.get_run_config_path(single_matching_run_name)
    if run_config_path is None:
        return False
    else:
        config.RunConfig.load(run_config_path)
        return True


@cli.command("abort", help="Abort execution of run NAME")
@_run_name_argument('name')
def abort_run(name: str):
    if not _load_config_by_run_name(name):
        return
    click.secho(f"You are about to kill run '{config.run_name()}'!")
    if user_confirmation_destructive(config.run_name()):
        system.abort_run(main_pid=fileio.get_saved_main_pid())
    else:
        click.echo("Not this time...")


@cli.command("continue", help="Continue aborted execution of aborted run NAME")
@_run_name_argument('name')
def continue_run(name: str):
    if not _load_config_by_run_name(name):
        return
    if system.process_alive(pid=fileio.get_saved_main_pid()):
        click.secho(f"Run already alive")
        return
    _run_standard_pipeline_in_background(continuing=True)


@cli.command("config-update", help="Update configuration of run NAME")
@click.option("--hard", is_flag=True, default=False, help="Flag to update config without detailed inspection")
@_run_config_option('new_config_filename')
@_run_name_argument('name')
def update_config_cmd(name: str, new_config_filename: str, hard: bool):
    if not _load_config_by_run_name(name):
        return
    update_config(new_config_filename, hard)


@cli.command("progress", help="Display progress for run NAME")
@click.option(
    "-f",
    "--follow",
    is_flag=True,
    default=False,
    help="Update progress bar each few seconds. Warning: clears terminal!",
)
@_run_name_argument('name')
def run_progress(name: str, follow: bool):
    if not _load_config_by_run_name(name):
        return
    if not follow:
        display_logs.print_pipelines_progress()
    else:
        while True:
            click.clear()
            display_logs.print_pipelines_progress()
            sleep(3)


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
@_run_name_argument('name')
def system_resources(name: str, include_previous_runs: bool, absolute_datetime: bool):
    if not _load_config_by_run_name(name):
        return
    display_logs.print_system_monitoring(
        include_previous_runs=include_previous_runs, evaluation_time_as_x=(not absolute_datetime)
    )


@cli.command("fix-failed", help="Fix failed pipelines")
@click.option("--hard", is_flag=True, default=False, help="If specified, removes all failed pipeline files entirely")
@_run_name_argument('name')
def fix_failed_pipelines(name: str, hard: bool):
    if not _load_config_by_run_name(name):
        return
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
@_run_name_argument('name')
def failures_cmd(name: str, pagesize: int, verbose: bool, failed: bool):
    if not _load_config_by_run_name(name):
        return
    pipeline_ids = fileio.get_failed_pipeline_ids() if failed else fileio.get_all_pipeline_ids()
    inspect.inspect_pipelines(pipeline_ids, page_size=pagesize, verbose=verbose, fix=False)


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


@cli.command("download-data-files")
def download_data_files():
    for data_file, gdrive_id, expected_md5 in (
        (fileio.DataFiles.sdgeant, '1ZTSrrAg2T8bvIDhPuh2ruVShmubwvTWG', '0cebc42f86e227e2fb2397dd46d7d981'),
        (fileio.DataFiles.atmos, '1qZfUNXAyqVg5HwH9BYUGVQ-UDsTwl4FQ', '254c7999be0a48bd65e4bc8cbea4867f'),
    ):
        if not data_file.exists():
            data_file.parent.mkdir(parents=True, exist_ok=True)
            gdown.download(id=gdrive_id, output=str(data_file))
        assert_md5sum(data_file, expected_md5)
