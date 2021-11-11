import pytest
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from time import sleep
from random import random

from typing import List

from tasdmc.steps.base.files import Files
from tasdmc.steps.processing.corsika import CorsikaCard, CorsikaOutputFiles
from tasdmc.steps.processing.particle_file_splitting import SplitParticleFiles
from tasdmc.steps.processing.dethinning import SplitParticleFile, DethinningOutputFiles
from tasdmc.steps.processing.corsika2geant import C2GInputFiles, C2GOutputFiles
from tasdmc.steps.processing.tothrow_generation import TothrowFile
from tasdmc.steps.processing.event_generation import EventFiles
from tasdmc.steps.processing.spectral_sampling import SpectralSampledEvents


CUR_DIR = Path(__file__).parent
MOCKS_DIR = CUR_DIR / 'mocks'

JUST_EXISTING = MOCKS_DIR / 'just_existing_file.smth'
DUMMY_PARTICLE = MOCKS_DIR / 'dummy_particle_file'
EMPTY = MOCKS_DIR / 'empty_file.smth'
ENDING_WITH_OK = MOCKS_DIR / 'file_with_ok_in_the_end.smth'


@pytest.fixture
def example_files():
    dethinning_output_1 = DethinningOutputFiles(dethinned_particle=DUMMY_PARTICLE, stdout=ENDING_WITH_OK, stderr=EMPTY)
    dethinning_output_2 = DethinningOutputFiles(dethinned_particle=DUMMY_PARTICLE, stdout=ENDING_WITH_OK, stderr=EMPTY)
    return [
        CorsikaCard(JUST_EXISTING),
        CorsikaOutputFiles(
            particle=DUMMY_PARTICLE,
            longtitude=MOCKS_DIR / 'corsika/example.long',
            stdout=MOCKS_DIR / 'corsika/good.stdout',
            stderr=MOCKS_DIR / 'corsika/empty.stderr',
        ),
        SplitParticleFiles(
            files=[DUMMY_PARTICLE],
            stderr=EMPTY,
            stdout=ENDING_WITH_OK,
        ),
        SplitParticleFile(DUMMY_PARTICLE),
        dethinning_output_1,
        C2GInputFiles(
            dethinning_outputs=[dethinning_output_1, dethinning_output_2],
            dethinned_files_listing=JUST_EXISTING,  # not checked
            corsika_event_name='doop',  # not checked
        ),
        # C2GOutputFiles(
        #     tile=MOCKS_DIR / 'MOCK_gea.dat',
        #     stderr=EMPTY,
        #     stdout=ENDING_WITH_OK,
        #     corsika_event_name='doop',
        # ),
        TothrowFile(JUST_EXISTING),
        EventFiles(
            merged_events_file=MOCKS_DIR / 'MOCK_EVENTS.dst.gz',
            stdout=ENDING_WITH_OK,
            stderr=EMPTY,
            concat_log=JUST_EXISTING,
            events_file_by_epoch={1: JUST_EXISTING},
            events_log_by_epoch={1: JUST_EXISTING},
            calibration_file_by_epoch={1: JUST_EXISTING},
        ),
        SpectralSampledEvents(
            events=MOCKS_DIR / 'MOCK_EVENTS.dst.gz',
            stdout=ENDING_WITH_OK,
            stderr=EMPTY,
        )
    ]


def _check_files(f: Files):
    sleep(random() * 0.2) # simulating different possible small offsets that may lead to race condition
    f.assert_files_are_ready()


def test_file_checks_threadsafe(example_files: List[Files]):
    for files in example_files:
        n_try = 3
        for _ in range(n_try):
            n_workers = 10
            with ProcessPoolExecutor(max_workers=n_workers) as executor:
                futures = [executor.submit(_check_files, f=files) for _ in range(n_workers)]
                [f.result() for f in futures]
    
