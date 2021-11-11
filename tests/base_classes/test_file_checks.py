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

JUST_EXISTING_FILE = MOCKS_DIR / 'just_existing_file.smth'
DUMMY_PARTICLE = MOCKS_DIR / 'dummy_particle_file'


@pytest.fixture
def example_files():
    return [
        CorsikaCard(JUST_EXISTING_FILE),
        CorsikaOutputFiles(
            particle=DUMMY_PARTICLE,
            longtitude=MOCKS_DIR / 'corsika/example.long',
            stdout=MOCKS_DIR / 'corsika/good.stdout',
            stderr=MOCKS_DIR / 'corsika/empty.stderr',
        )
    ]


def _check_files(f: Files):
    # simulating different possible small offsets that may lead to race condition
    sleep(random() * 0.2)
    f.assert_files_are_ready()


def test_file_checks_threadsafe(example_files: List[Files]):
    for files in example_files:
        n_try = 3
        for _ in range(n_try):
            n_workers = 10
            with ProcessPoolExecutor(max_workers=n_workers) as executor:
                futures = [executor.submit(_check_files, f=files) for _ in range(n_workers)]
                [f.result() for f in futures]
    
