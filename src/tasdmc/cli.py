"""Command line interface used by click package to create `tasdmc` executable"""

import click

from tasdmc import config, fileio, system, pipeline, cleanup
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
        help='run configuration .yaml file',
    )


@cli.command("run", help="Run simulation")
@_run_config_option('config_filename')
def run(config_filename):
    config.load(config_filename)
    config.validate()
    fileio.prepare_run_dir()
    pipeline.run_standard_pipeline()


@cli.command("resources", help="Estimate resources that will be taken up by a run")
@_run_config_option('config_filename')
def rasources(config_filename: str):
    config.load(config_filename)
    click.secho(f"{config.run_name()} resources:", bold=True)
    click.secho(f"Processes: {config.used_processes()} (on {system.n_cpu()} CPUs)")
    click.secho(f"RAM: {config.used_ram()} Gb ({system.available_ram():.2f} Gb available)")


# esixting run commands


def _run_name_argument(param_name: str):
    return click.argument(param_name, type=click.STRING)


@cli.command("ps", help="Display run NAME's processes status and print last messages from worker processes")
@_run_name_argument('name')
@click.option("-n", "n_last_messages", default=1, help="Number of messages from worker processes to print")
def abort(name: str, n_last_messages: int):
    config.load(fileio.get_run_config_path(name))

    main_process_id = fileio.get_saved_main_process_id()
    system.print_process_status(main_process_id)

    worker_pids = system.get_children_process_ids(main_process_id)
    display_progress.print_multiprocessing_debug(worker_pids, n_last_messages)


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
def abort(name: str):
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
