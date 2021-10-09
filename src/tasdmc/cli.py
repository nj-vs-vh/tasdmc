"""Command line interface used by click package to create `tasdmc` executable"""

import click
from tasdmc import config, fileio
from tasdmc.steps import CorsikaCardsGeneration, CorsikaSimulation


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-c', '--config', 'run_config_filename', default='run.yaml')
def run(run_config_filename):
    config.load(run_config_filename)
    fileio.prepare_run_dir()
    for Step in (CorsikaCardsGeneration, CorsikaSimulation):
        Step.validate_config()

    ccg = CorsikaCardsGeneration.create_and_run()
    for cs in CorsikaSimulation.from_corsika_cards_generation(ccg):
        cs.run()
