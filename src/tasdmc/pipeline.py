from concurrent.futures import ProcessPoolExecutor

from tasdmc import config
from tasdmc.steps import (
    CorsikaCardsGenerationStep,
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
    CleanupStep,
)


def run_standard_pipeline():

    cards_generation = CorsikaCardsGenerationStep.create_and_run()
    for corsika_step in CorsikaStep.from_corsika_cards_generation(cards_generation):
        corsika_step.run()

        particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika_step)
        particle_file_splitting.run()

        dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
        for dethinning in dethinning_steps:
            dethinning.run()

        corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)
        corsika2geant.run()

        cleanup = CleanupStep.from_steps_to_cleanup(
            cleanup_steps=[particle_file_splitting, *dethinning_steps], must_be_completed=corsika2geant
        )
        cleanup.run()
