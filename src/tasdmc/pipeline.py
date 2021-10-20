from concurrent.futures import ProcessPoolExecutor, Future

from typing import List

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

    with ProcessPoolExecutor(max_workers=config.used_processes()) as executor:
        futures: List[Future] = []

        for corsika_step in CorsikaStep.from_corsika_cards_generation(cards_generation):
            corsika_step.run(executor, futures)

            particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika_step)
            particle_file_splitting.run(executor, futures)

            dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
            for dethinning in dethinning_steps:
                dethinning.run(executor, futures)

            corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)
            corsika2geant.run(executor, futures)

            cleanup = CleanupStep.from_steps_to_cleanup(
                cleanup_steps=[particle_file_splitting, *dethinning_steps], must_be_completed=corsika2geant
            )
            cleanup.run(executor, futures)

        for f in futures:
            f.result()
