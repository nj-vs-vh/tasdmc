from concurrent.futures import ProcessPoolExecutor, Future
from pathlib import Path
import time

from typing import List, Optional

from tasdmc import config, fileio, system
from tasdmc.steps import (
    CorsikaCardsGenerationStep,
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
    TothrowGenerationStep,
    EventsGenerationStep,
    SpectralSamplingStep,
    FileInFileOutPipelineStep,
)
from tasdmc.system.monitor import run_system_monitor
from tasdmc.utils import batches


def standard_pipeline_steps(
    cards_generation_step: Optional[CorsikaCardsGenerationStep],
    card_paths_override: Optional[List[Path]] = None,
) -> List[FileInFileOutPipelineStep]:
    """List of pipeline steps *in order of optimal execution*"""
    steps: List[FileInFileOutPipelineStep] = []
    if cards_generation_step:
        corsika_steps = CorsikaStep.from_corsika_cards_generation(cards_generation_step)
    else:
        if card_paths_override:
            corsika_steps = CorsikaStep.from_corsika_card_paths(card_paths_override)
        else:
            raise ValueError(
                "standard pipeline steps may be created from either CorsikaCardsGenerationStep "
                + "instance or list of paths to CORSIKA cards"
            )

    # TODO: make batch size configurable -------------------> here?
    for corsika_steps_batch in batches(corsika_steps, config.used_processes()):
        steps.extend(corsika_steps_batch)
        for corsika_step in corsika_steps_batch:
            particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika_step)
            steps.append(particle_file_splitting)
            dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
            steps.extend(dethinning_steps)
            corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)
            steps.append(corsika2geant)
            tothrow_gen = TothrowGenerationStep.from_corsika2geant(corsika2geant)
            steps.append(tothrow_gen)
            events_generation = EventsGenerationStep.from_corsika2geant_with_tothrow(corsika2geant, tothrow_gen)
            steps.append(events_generation)
            spctr_sampling = SpectralSamplingStep.from_events_generation(events_generation)
            steps.append(spctr_sampling)
    return steps


def run_standard_pipeline(continuing: bool):
    system.set_process_title("tasdmc main")
    fileio.prepare_run_dir(continuing)
    cards_generation = CorsikaCardsGenerationStep.create_and_run()
    steps = standard_pipeline_steps(cards_generation_step=cards_generation)
    # workaround; TODO: pack steps sequence in a pipeline class
    config.validate(set(step.__class__ for step in steps))
    system.run_in_background(run_system_monitor, keep_session=True)
    n_processes = config.used_processes()
    with ProcessPoolExecutor(
        max_workers=n_processes, initializer=lambda: system.set_process_title("tasdmc worker")
    ) as executor:
        futures_queue: List[Future] = []
        for step in steps:
            step.schedule(executor, futures_queue)
        for f in futures_queue:
            time.sleep(1)
            f.result()
