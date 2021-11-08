"""Command line interface used by click package to create `tasdmc` executable"""

try:
    import click
    from pathlib import Path
    import gdown
    from gdown.cached_download import assert_md5sum

    from tasdmc import __version__
    from tasdmc import config, fileio, system, pipeline, failures, extract_calibration
    from tasdmc.logs import display as display_logs
    from tasdmc.config.actions import update_config, view_config
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
        default='run.yaml',  # TODO: remove default, make this required option in prod
        show_default=True,
        type=click.Path(),
        help='run configuration .yaml file',
    )


def _run_standard_pipeline_in_background(continuing: bool):
    system.run_in_background(pipeline.run_standard_pipeline, continuing)
    click.echo(f"Running in the background. Use 'tasdmc ps {config.run_name()}' to check run status")


@cli.command("run", help="Run simulation")
@_run_config_option('config_filename')
def run(config_filename):
    config.load(config_filename)
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
            click.echo(f"Did you mean '{single_matching_run_name}?' [Yes, no]")
            confirmation = input('> ')
            if confirmation != 'no':
                click.echo()
                run_config_path = fileio.get_run_config_path(single_matching_run_name)
    if run_config_path is None:
        return False
    else:
        config.load(run_config_path)
        return True


@cli.command("abort", help="Abort execution of run NAME")
@_run_name_argument('name')
def abort_run(name: str):
    if not _load_config_by_run_name(name):
        return
    click.secho(f"You are about to kill run '{config.run_name()}'!\nIf you are sure, type its name again below:")
    run_name_confirmation = input('> ')
    if run_name_confirmation == config.run_name():
        system.abort_run(main_pid=fileio.get_saved_main_pid())


@cli.command("continue", help="Continue aborted execution of aborted run NAME")
@_run_name_argument('name')
def continue_run(name: str):
    if not _load_config_by_run_name(name):
        return
    if system.process_alive(pid=fileio.get_saved_main_pid()):
        click.secho(f"Run already alive")
        return
    _run_standard_pipeline_in_background(continuing=True)


@cli.command("config", help="Operations with configuration of run NAME: view, update")
@_run_config_option('new_config_filename')
@click.argument(
    'action', type=click.STRING, shell_complete=lambda *p: [a for a in ['update', 'view'] if a.startswith(p[2])]
)
@_run_name_argument('name')
def update_config_in_run(action: str, name: str, new_config_filename: str):
    if not _load_config_by_run_name(name):
        return
    if action == 'update':
        update_config(new_config_filename)
    elif action == 'view':
        view_config()
    else:
        click.echo(f"Unknown action '{action}'; available actions are 'update' and 'view'")


@cli.command("progress", help="Display progress for run NAME")
@_run_name_argument('name')
def run_progress(name: str):
    if not _load_config_by_run_name(name):
        return
    display_logs.print_pipelines_progress()


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
    help="If set to True, X axis on plots represent absolute datetimes in UTC; otherwise Run evaluation Time is used",
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


failures_cmd_actions = ['total-cleanup']


@cli.command(
    "failures",
    help="Failure management for run NAME. ACTIONs: " + ', '.join(failures_cmd_actions),
)
@click.argument(
    'action', type=click.STRING, shell_complete=lambda *p: [a for a in failures_cmd_actions if a.startswith(p[2])]
)
@_run_name_argument('name')
def failures_cmd(name: str, action: str):
    if action not in failures_cmd_actions:
        click.echo(
            f"Unknown action '{action}'. Available actions are:\n" + '\n'.join([f'\t{a}' for a in failures_cmd_actions])
        )
        return
    if not _load_config_by_run_name(name):
        return

    failed_pipeline_files = fileio.get_failed_pipeline_files()
    if not failed_pipeline_files:
        click.echo("No failed pipelines found")
        return

    if action == 'total-cleanup':
        click.echo(
            f"Failed pipelines to be {click.style('completely', bold=True)} removed:\n"
            + "\n".join([f'\t{p.name}' for p in failed_pipeline_files])
        )
        click.echo("\nType 'yes' to confirm")
        confirmation = input('> ')
        if confirmation == 'yes':
            for fp in failed_pipeline_files:
                failures.delete_all_files_from_failed_pipeline(fp)


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
        pass
        if not data_file.exists():
            data_file.parent.mkdir(parents=True, exist_ok=True)
            gdown.download(id=gdrive_id, output=str(data_file))
        assert_md5sum(data_file, expected_md5)
