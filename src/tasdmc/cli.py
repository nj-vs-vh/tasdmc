"""Command line interface used by click package to create `tasdmc` executable"""

import click

from tasdmc import config, fileio
from tasdmc.steps import CorsikaCardsGenerationStep, CorsikaStep, ParticleFileSplittingStep, DethinningStep


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-c', '--config', 'run_config_filename', default='run.yaml')
def run(run_config_filename):
    config.load(run_config_filename)
    fileio.prepare_run_dir()
    for Step in (CorsikaCardsGenerationStep, CorsikaStep, ParticleFileSplittingStep, DethinningStep):
        Step.validate_config()

    cards_generation = CorsikaCardsGenerationStep.create_and_run()
    for corsika in CorsikaStep.from_corsika_cards_generation(cards_generation):
        corsika.run()
        particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika)
        particle_file_splitting.run()
        for dethinning in DethinningStep.from_particle_file_splitting_step(particle_file_splitting):
            dethinning.run()
