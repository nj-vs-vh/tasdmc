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
from tasdmc.utils import batches


def run_standard_pipeline():
    cards_generation = CorsikaCardsGenerationStep.create_and_run()
    n_processes = config.used_processes()
    with ProcessPoolExecutor(max_workers=n_processes) as executor:
        futures_queue: List[Future] = []

        corsika_steps = CorsikaStep.from_corsika_cards_generation(cards_generation)
        for corsika_steps_batch in batches(corsika_steps, n_processes):
            for corsika_step in corsika_steps_batch:  # first running a batch of corsikas in parallel
                corsika_step.run(executor, futures_queue)

            for corsika_step in corsika_steps_batch:
                particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika_step)
                dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
                corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)
                cleanup = CleanupStep.from_steps_to_cleanup(
                    cleanup_steps=[particle_file_splitting, *dethinning_steps], must_be_completed=corsika2geant
                )

                if not corsika2geant.output.files_were_produced():  # TODO: remove this
                    particle_file_splitting.run(executor, futures_queue)
                    for dethinning in dethinning_steps:
                        dethinning.run(executor, futures_queue)
                    corsika2geant.run(executor, futures_queue)
                    cleanup.run(executor, futures_queue)

        for f in futures_queue:
            f.result()
