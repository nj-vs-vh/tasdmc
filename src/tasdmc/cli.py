"""Command line interface used by click package to create `tasdmc` executable"""

import click
from tasdmc import config, fileio
from tasdmc.steps import CorsikaCardsGenerationStep, CorsikaStep


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-c', '--config', 'run_config_filename', default='run.yaml')
def run(run_config_filename):
    config.load(run_config_filename)
    fileio.prepare_run_dir()
    for Step in (CorsikaCardsGenerationStep, CorsikaStep):
        Step.validate_config()

    cards_generation_step = CorsikaCardsGenerationStep.create_and_run()
    for corsika_step in CorsikaStep.from_corsika_cards_generation(cards_generation_step):
        corsika_step.run()
