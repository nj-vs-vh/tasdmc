from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import config
from tasdmc.c_routines_wrapper import split_thinned_corsika_output

from tasdmc.steps.base import NotAllRetainedFiles, PipelineStep
from .corsika import CorsikaStep, CorsikaOutputFiles
from tasdmc.steps.utils import check_particle_file_contents, check_file_is_empty, check_last_line_contains


@dataclass
class SplitParticleFiles(NotAllRetainedFiles):
    files: List[Path]
    stderr: Path
    stdout: Path

    @property
    def must_exist(self) -> List[Path]:
        return self.files

    @property
    def not_retained(self) -> List[Path]:
        return self.files

    @classmethod
    def from_corsika_output_files(cls, cof: CorsikaOutputFiles) -> SplitParticleFiles:
        n_split = _n_split_from_config()
        return SplitParticleFiles(  # in sync with how these names are generated in C routine
            files=[cof.particle.with_suffix(f'.p{i+1:02d}') for i in range(n_split)],
            stdout=cof.particle.with_suffix(".split.stdout"),
            stderr=cof.particle.with_suffix(".split.stderr"),
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr)
        check_last_line_contains(self.stdout, "OK")
        for f in self.files:
            check_particle_file_contents(f)


@dataclass
class ParticleFileSplittingStep(PipelineStep):
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
            previous_steps=[corsika_step],
        )

    @property
    def description(self) -> str:
        return f"Splitting CORSIKA particle file {self.input_.particle.name} into {self.split_to} parts"

    def _run(self):
        split_thinned_corsika_output(self.input_.particle, self.split_to, self.output.stdout, self.output.stderr)

    @classmethod
    def validate_config(self):
        _n_split_from_config()


def _n_split_from_config() -> int:
    n_split = config.get_key('dethinning.n_parallel', default=config.used_processes())
    if isinstance(n_split, int) and n_split > 0:
        return n_split
    else:
        raise ValueError("dethinning.n_parallel is expected to be non-negative integer")
