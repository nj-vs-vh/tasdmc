from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import config
from tasdmc.c_routines_wrapper import split_thinned_corsika_output

from tasdmc.steps.base import NotAllRetainedFiles, FileInFileOutPipelineStep
from .corsika import CorsikaStep, CorsikaOutputFiles
from tasdmc.steps.utils import check_particle_file_contents


@dataclass
class SplitParticleFiles(NotAllRetainedFiles):
    files: List[Path]

    @property
    def must_exist(self) -> List[Path]:
        return self.files

    @property
    def not_retained(self) -> List[Path]:
        return self.files

    @classmethod
    def from_corsika_output_files(cls, cof: CorsikaOutputFiles) -> SplitParticleFiles:
        n_split = _n_split_from_config()
        return cls(  # in sync with how these names are generated in C routine
            [cof.particle.with_suffix(f'.p{i+1:02d}') for i in range(n_split)]
        )

    def _check_contents(self):
        for f in self.files:
            check_particle_file_contents(f)


@dataclass
class ParticleFileSplittingStep(FileInFileOutPipelineStep):
    input_: CorsikaOutputFiles
    output: SplitParticleFiles

    @property
    def split_to(self) -> int:
        return len(self.output.files)

    @classmethod
    def from_corsika_step(cls, corsika_step: CorsikaStep) -> ParticleFileSplittingStep:
        return ParticleFileSplittingStep(
            input_=corsika_step.output,
            output=SplitParticleFiles.from_corsika_output_files(corsika_step.output),
            previous_step=corsika_step,
        )

    @property
    def description(self) -> str:
        return f"Splitting CORSIKA particle file {self.input_.particle.name} into {self.split_to} parts"

    def _run(self):
        split_thinned_corsika_output(self.input_.particle, self.split_to)

    @classmethod
    def validate_config(self):
        _n_split_from_config()


def _n_split_from_config() -> int:
    n_split = config.get_key('dethinning.particle_file_split_to', default=config.used_processes())
    if isinstance(n_split, int) and n_split > 0:
        return n_split
    else:
        raise config.BadConfigValue(f"dethinning.particle_file_split_to is expected to be non-negative integer")