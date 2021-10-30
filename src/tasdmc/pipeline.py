from concurrent.futures import ProcessPoolExecutor, Future

from typing import List

from tasdmc import config, fileio, system
from tasdmc.steps import (
    CorsikaCardsGenerationStep,
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
    TothrowGenerationStep,
    EventsGenerationStep,
)
from tasdmc.utils import batches


def run_standard_pipeline(continuing: bool):
    system.set_process_title("tasdmc main")
    fileio.prepare_run_dir(continuing)

    cards_generation = CorsikaCardsGenerationStep.create_and_run()
    n_processes = config.used_processes()
    with ProcessPoolExecutor(
        max_workers=n_processes, initializer=lambda: system.set_process_title("tasdmc worker")
    ) as executor:
        futures_queue: List[Future] = []

        corsika_steps = CorsikaStep.from_corsika_cards_generation(cards_generation)
        for corsika_steps_batch in batches(corsika_steps, n_processes):
            for corsika_step in corsika_steps_batch:  # first running a batch of corsikas in parallel
                corsika_step.schedule(executor, futures_queue)

            for corsika_step in corsika_steps_batch:
                particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika_step)
                dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
                corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)

                if not (
                    config.get_key('dethinning._try_to_skip', default=False)
                    and corsika2geant.output.files_were_produced()
                ):
                    particle_file_splitting.schedule(executor, futures_queue)
                    for dethinning in dethinning_steps:
                        dethinning.schedule(executor, futures_queue)
                    corsika2geant.schedule(executor, futures_queue)

                tothrow_gen = TothrowGenerationStep.from_corsika2geant(corsika2geant)
                tothrow_gen.schedule(executor, futures_queue)

                events_generation = EventsGenerationStep.from_corsika2geant_with_tothrow(corsika2geant, tothrow_gen)
                events_generation.schedule(executor, futures_queue)

        for f in futures_queue:
            f.result()
