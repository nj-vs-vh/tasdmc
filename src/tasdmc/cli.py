"""Command line interface used by click package to create `tasdmc` executable"""

import click

from tasdmc import config, fileio, resources, pipeline


def run_config_option():
    return click.option(
        '-c',
        '--config',
        'run_config_filename',
        default='run.yaml',
        show_default=True,
        help='run configuration .yaml file',
    )


@click.group()
def cli():
    pass


@cli.command("resources", help="Estimate resources that will be taken up by a run")
@run_config_option()
def rasources(run_config_filename):
    config.load(run_config_filename)
    click.secho(f"{config.run_name()} resources:", bold=True)
    click.secho(f"Processes: {config.used_processes()} (on {resources.n_cpu()} CPUs)")
    click.secho(f"RAM: {config.used_ram()} Gb ({resources.available_ram():.2f} Gb available)")


@cli.command("run", help="Run simulation pipeline")
@run_config_option()
def run(run_config_filename):
    config.load(run_config_filename)
    config.validate()
    fileio.prepare_run_dir()
    pipeline.run_standard_pipeline()
