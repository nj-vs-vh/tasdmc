from typing import List, Type

from .base import FileInFileOutStep

from .corsika_cards_generation import CorsikaCardsGenerationStep
from .processing.corsika import CorsikaStep
from .processing.particle_file_splitting import ParticleFileSplittingStep
from .processing.dethinning import DethinningStep
from .processing.corsika2geant import Corsika2GeantStep


all_steps: List[Type[FileInFileOutStep]] = [
    CorsikaCardsGenerationStep,
    CorsikaStep,
    ParticleFileSplittingStep,
    DethinningStep,
    Corsika2GeantStep,
]


__all__: List[str] = [step.__name__ for step in all_steps]
