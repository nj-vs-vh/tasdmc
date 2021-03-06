from concurrent.futures import ProcessPoolExecutor, Future, wait
import multiprocessing as mp
from pathlib import Path
from ctypes import c_int8
from collections import defaultdict
from itertools import chain

from typing import List, Union

from tasdmc import config, fileio
from tasdmc.system import monitor, resources, processes, run_in_background
from tasdmc.steps import (
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
    Corsika2GeantParallelProcessStep,
    Corsika2GeantParallelMergeStep,
    TothrowGenerationStep,
    EventsGenerationStep,
    SpectralSamplingStep,
    PipelineStep,
    ReconstructionStep,
    TawikiDumpStep,
)
from tasdmc.steps.aggregation import TawikiDumpsMergeStep, ReconstructedEventsArchivingStep
from tasdmc.steps.corsika_cards_generation import generate_corsika_cards
from tasdmc.steps.base.step_status_shared import set_step_statuses_array
from tasdmc.utils import batches


def get_steps_queue(
    corsika_card_paths: List[Path],
    include_aggregation_steps: bool = True,
    disable_batching: bool = False,
) -> List[PipelineStep]:
    """
    Args:
        corsika_card_paths (List[Path]): List of paths to CORSIKA input cards; usually generated
                                         with generate_corsika_cards, but may also be manually crafted
        include_aggregation_steps (bool, optional): Whether to include multipipeline aggregation steps
                                                    (e.g. dump params from all .dst.gz into a csv file).
                                                    Defaults to True.
        batched (bool, optional): Whether to batch steps by the number of processes used (e.g. 16 CORSIKA
                                  steps, then 16 splitting steps, etc). Setting the flag to False is the same
                                  as setting the batch size to the number of pipelines (i.e. all CORSIKA steps,
                                  then all splitting steps, etc). Defaults to True.

    Returns:
        List[PipelineStep]: A list of pipeline steps in order of optimal execution
    """
    all_corsika_steps = CorsikaStep.from_corsika_cards(corsika_card_paths)
    queue: List[PipelineStep] = []
    
    legacy_c2g_step = bool(config.get_key("pipeline.legacy_corsika2geant", default=True))

    archive_reconstructed_events = bool(config.get_key("pipeline.archive_all_reconstructed_events", default=True))
    reconstruction_steps_by_log10Emin = defaultdict(list)

    add_tawiki_steps = bool(config.get_key("pipeline.produce_tawiki_dumps", default=False))
    tawiki_dump_steps_by_log10Emin = defaultdict(list)

    try:
        batch_size_multiplier = float(config.get_key("pipeline.batch_size_multiplier", default=2.0))
    except ValueError:
        batch_size_multiplier = 0
    if disable_batching:  # explicit flag takes precedence over config value
        batch_size = len(all_corsika_steps)
    else:
        batch_size = int(resources.used_processes() * batch_size_multiplier) or len(all_corsika_steps)

    for corsika_steps_batch in batches(all_corsika_steps, batch_size):
        queue.extend(corsika_steps_batch)
        c2g_steps_batch: List[Union[Corsika2GeantStep, Corsika2GeantParallelMergeStep]] = []
        for corsika_step in corsika_steps_batch:
            particle_file_splitting = ParticleFileSplittingStep.from_corsika_step(corsika_step)
            queue.append(particle_file_splitting)
            dethinning_steps = DethinningStep.from_particle_file_splitting_step(particle_file_splitting)
            if legacy_c2g_step:
                # all dethinnings are executed first, then converted to tile file in bulk with legacy corsika2geant
                queue.extend(dethinning_steps)
                corsika2geant = Corsika2GeantStep.from_dethinning_steps(dethinning_steps)
            else:
                # each dethinning step is immediately followed by c2g_parallel_process
                c2g_process_steps = []
                for dethinning_step in dethinning_steps:
                    c2g_process = Corsika2GeantParallelProcessStep.from_dethinning_step(dethinning_step)
                    c2g_process_steps.append(c2g_process)
                    queue.append(dethinning_step)
                    queue.append(c2g_process)
                corsika2geant = Corsika2GeantParallelMergeStep.from_c2g_parallel_process_steps(c2g_process_steps)
            queue.append(corsika2geant)
            c2g_steps_batch.append(corsika2geant)
        # after c2g, no cleanup is done between steps so we can launch them in batches again to avoid
        # pipeline jam (later steps sit in queue and just wait for the previous ones)
        tothrow_steps_batch = [TothrowGenerationStep.from_corsika2geant(c2g) for c2g in c2g_steps_batch]
        queue.extend(tothrow_steps_batch)
        event_gen_steps_batch = [
            EventsGenerationStep.from_corsika2geant_with_tothrow(c2g, tothrow)
            for (c2g, tothrow) in zip(c2g_steps_batch, tothrow_steps_batch)
        ]
        queue.extend(event_gen_steps_batch)
        # larger batch: original batch size * number of minimal energies to sample
        spectral_sampling_batch = list(
            chain.from_iterable(
                SpectralSamplingStep.from_events_generation(event_gen) for event_gen in event_gen_steps_batch
            )
        )
        queue.extend(spectral_sampling_batch)

        reconstruction_steps_batch = [
            ReconstructionStep.from_spectral_sampling(spectral_sampling)
            for spectral_sampling in spectral_sampling_batch
        ]
        queue.extend(reconstruction_steps_batch)

        for reco in reconstruction_steps_batch:
            reconstruction_steps_by_log10Emin[reco.input_.log10E_min].append(reco)
            if add_tawiki_steps:
                tawiki_dump_step = TawikiDumpStep.from_reconstruction_step(reco)
                queue.append(tawiki_dump_step)
                tawiki_dump_steps_by_log10Emin[reco.input_.log10E_min].append(tawiki_dump_step)

    if include_aggregation_steps:
        if add_tawiki_steps:
            for log10E_min, tawiki_dump_steps in tawiki_dump_steps_by_log10Emin.items():
                queue.append(TawikiDumpsMergeStep.from_tawiki_dump_steps(tawiki_dump_steps, log10E_min))
        if archive_reconstructed_events:
            for log10E_min, reco_steps in reconstruction_steps_by_log10Emin.items():
                queue.append(ReconstructedEventsArchivingStep.from_reconstruction_steps(reco_steps, log10E_min))
    return queue


def with_pipelines_mask(steps: List[PipelineStep]) -> List[PipelineStep]:
    pipelines_mask: List[str] = config.get_key('debug.pipelines_mask', default=[])
    if not pipelines_mask:
        return steps
    else:
        return [s for s in steps if s.pipeline_id in pipelines_mask]


def run_simulation(dry: bool = False):
    processes.set_process_title("tasdmc main")
    processes.setup_safe_abort_signal_listener()
    fileio.save_main_process_pid()

    steps = get_steps_queue(corsika_card_paths=generate_corsika_cards())
    steps = with_pipelines_mask(steps)
    config.validate(set(step.__class__ for step in steps))

    if dry:
        return

    sysmon_pid = run_in_background(monitor.run_system_monitor, keep_session=True)

    for idx, step in enumerate(steps):
        step.set_index(idx)
    shared_step_statuses_array = mp.Array(c_int8, len(steps), lock=True)  # initially all zeros = steps pending

    def init_worker_process(shared_array):
        processes.set_process_title("tasdmc worker")
        set_step_statuses_array(shared_array)

    with ProcessPoolExecutor(
        max_workers=resources.used_processes(),
        initializer=init_worker_process,  # shared array is sent to each worker process here
        initargs=(shared_step_statuses_array,),
    ) as executor:
        futures_queue: List[Future] = []
        for step in steps:
            step.schedule(executor, futures_queue)
        wait(futures_queue)

    processes.kill_process(sysmon_pid)
