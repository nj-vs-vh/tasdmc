"""Command line interface used by click package to create `tasdmc` executable"""

import click
from tasdmc import config, fileio
from tasdmc.steps import CorsikaCardsGeneration


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-c', '--config', 'config_filename', default='run.yaml')
def run(config_filename):
    config.load(config_filename)
    fileio.prepare_run_dir()
    ccg = CorsikaCardsGeneration.create_and_run()
