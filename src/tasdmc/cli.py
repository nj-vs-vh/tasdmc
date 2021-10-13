"""Command line interface used by click package to create `tasdmc` executable"""

import click

from tasdmc import config, fileio
from tasdmc.steps import CorsikaCardsGenerationStep, CorsikaStep, ParticleFileSplittingStep, DethinningStep, Corsika2GeantStep


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-c', '--config', 'run_config_filename', default='run.yaml')
def run(run_config_filename):
    config.load(run_config_filename)
    config.validate()

    fileio.prepare_run_dir()

    cards_generation = CorsikaCardsGenerationStep.create_and_run()
    for corsika in CorsikaStep.from_corsika_cards_generation(cards_generation):
        corsika.run()

        particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika)
        particle_file_splitting.run()

        dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
        for dethinning in dethinning_steps:
            dethinning.run()

        corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)
        corsika2geant.run()
