from concurrent.futures import ProcessPoolExecutor, Future, wait
import multiprocessing as mp
from pathlib import Path
from ctypes import c_int8

from typing import List

from tasdmc import config, fileio, system
from tasdmc.steps import (
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
    TothrowGenerationStep,
    EventsGenerationStep,
    SpectralSamplingStep,
    PipelineStep,
    ReconstructionStep,
)
from tasdmc.steps.corsika_cards_generation import generate_corsika_cards
from tasdmc.system.monitor import run_system_monitor
from tasdmc.steps.base.step_status_shared import set_step_statuses_array
from tasdmc.utils import batches


def standard_simulation_steps(corsika_card_paths: List[Path]) -> List[PipelineStep]:
    """List of pipeline steps *in order of optimal execution*"""
    steps: List[PipelineStep] = []
    corsika_steps = CorsikaStep.from_corsika_cards(corsika_card_paths)

    # TODO: make batch size configurable here?
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
            for spctr_sampling in SpectralSamplingStep.from_events_generation(events_generation):
                steps.append(spctr_sampling)
                reconstruction = ReconstructionStep.from_spectral_sampling(spctr_sampling)
                # steps.append(reconstruction)
    return steps


def with_pipelines_mask(steps: List[PipelineStep]) -> List[PipelineStep]:
    pipelines_mask: List[str] = config.get_key('debug.pipelines_mask', default=False)
    if not pipelines_mask:
        return steps
    else:
        return [s for s in steps if s.pipeline_id in pipelines_mask]


def run_standard_pipeline(continuing: bool):
    system.set_process_title("tasdmc main")
    fileio.prepare_run_dir(continuing)
    steps = standard_simulation_steps(corsika_card_paths=generate_corsika_cards())
    steps = with_pipelines_mask(steps)
    # workaround; TODO: pack steps sequence in a pipeline class
    config.validate(set(step.__class__ for step in steps))
    system.run_in_background(run_system_monitor, keep_session=True)

    step_indices = list(range(len(steps)))
    for step, idx in zip(steps, step_indices):
        step.set_index(idx)
    shared_array = mp.Array(c_int8, len(steps), lock=True)  # initially all zeros = steps pending

    def init_worker_process(shared_array):
        system.set_process_title("tasdmc worker")
        set_step_statuses_array(shared_array)

    n_processes = config.used_processes()
    with ProcessPoolExecutor(
        max_workers=n_processes, initializer=init_worker_process, initargs=(shared_array,)
    ) as executor:
        futures_queue: List[Future] = []
        for step in steps:
            step.schedule(executor, futures_queue)
        wait(futures_queue)
