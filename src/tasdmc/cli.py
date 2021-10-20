"""Command line interface used by click package to create `tasdmc` executable"""

import click

from tasdmc import config, fileio, system, pipeline


def run_config_option(param_name: str):
    return click.option(
        '-c',
        '--config',
        param_name,
        default='run.yaml',
        show_default=True,
        help='run configuration .yaml file',
    )


def run_name_argument(param_name: str):
    return click.argument(param_name, type=click.STRING)


@click.group()
def cli():
    pass


@cli.command("run", help="Run simulation pipeline")
@run_config_option('config_filename')
def run(config_filename):
    config.load(config_filename)
    config.validate()
    fileio.prepare_run_dir()
    pipeline.run_standard_pipeline()


@cli.command("resources", help="Estimate resources that will be taken up by a run")
@run_config_option('config_filename')
def rasources(config_filename: str):
    config.load(config_filename)
    click.secho(f"{config.run_name()} resources:", bold=True)
    click.secho(f"Processes: {config.used_processes()} (on {system.n_cpu()} CPUs)")
    click.secho(f"RAM: {config.used_ram()} Gb ({system.available_ram():.2f} Gb available)")


@cli.command("abort", help="Abort execution of run specified by NAME. This will kill all processes in specified run!")
@run_name_argument('name')
def abort(name: str):
    config.load(fileio.get_run_config_path(name))

    main_run_process_pid_file = fileio.saved_main_process_id_file()
    if not main_run_process_pid_file.exists():
        click.echo(f"No saved main process ID found for run '{name}'")
        return
    click.secho(f"You are about to kill all processes in run '{name}'!\nIf you are sure, type its name again below:")
    run_name_confirmation = input('> ')
    if name == run_name_confirmation:
        main_run_process_pid = int(main_run_process_pid_file.read_text())
        system.kill_all_run_processes_by_main_process_id(main_run_process_pid)
    else:
        click.secho("Typed run name doesn't match")
