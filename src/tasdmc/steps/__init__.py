from typing import List, Type

from .base import PipelineStep

from .processing.corsika import CorsikaStep
from .processing.particle_file_splitting import ParticleFileSplittingStep
from .processing.dethinning import DethinningStep
from .processing.corsika2geant import Corsika2GeantStep
from .processing.tothrow_generation import TothrowGenerationStep
from .processing.event_generation import EventsGenerationStep
from .processing.spectral_sampling import SpectralSamplingStep
from .processing.reconstruction import ReconstructionStep
from .processing.tawiki_dump import TawikiDumpStep, TawikiDumpsMergeStep


all_steps: List[Type[PipelineStep]] = [
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
    TothrowGenerationStep,
    EventsGenerationStep,
    SpectralSamplingStep,
    ReconstructionStep,
    TawikiDumpStep,
    TawikiDumpsMergeStep,
]


__all__: List[str] = [step.__name__ for step in all_steps]
