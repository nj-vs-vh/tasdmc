from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tasdmc import fileio
from ..base import Files, PipelineStep
from .spectral_sampling import SpectralSampledEvents, SpectralSamplingStep


@dataclass
class ReconstructedEvents(Files):
    rufptn_dst: Path
    rufptn_log: Path
    rufldf_dst: Path
    rufldf_log: Path

    @classmethod
    def from_spectral_sampled_events(cls, sse: SpectralSampledEvents) -> ReconstructedEvents:
        base_name = '.'.join([sse.events.name, *[suff for suff in sse.events.suffixes if suff not in {'.dst', '.gz'}]])
        dir = fileio.reconstruction_dir()
        return ReconstructedEvents(
            rufptn_dst=dir / (base_name + ".rufptn.dst.gz"),
            rufptn_log=dir / (base_name + ".rufptn.log"),
            rufldf_dst=dir / (base_name + ".rufldf.dst.gz"),
            rufldf_log=dir / (base_name + ".rufldf.log"),
        )


@dataclass
class ReconstructionStep(PipelineStep):
    input_: SpectralSampledEvents
    output: ReconstructedEvents

    @property
    def description(self) -> str:
        return f"Reconstruction of {self.input_.events}"

    @classmethod
    def from_spectral_sampling(cls, spectral_sampling: SpectralSamplingStep) -> ReconstructionStep:
        return ReconstructionStep(
            input_=spectral_sampling.output,
            output=ReconstructedEvents.from_spectral_sampled_events(spectral_sampling.output),
            previous_steps=[spectral_sampling],
        )

    def _run(self):
        pass
