from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import run_dethinning

from tasdmc.steps.base import NotAllRetainedFiles, PipelineStep
from tasdmc.steps.utils import check_particle_file_contents, check_file_is_empty, check_last_line_contains

from .particle_file_splitting import SplitParticleFiles, ParticleFileSplittingStep


@dataclass
class SplitParticleFile(NotAllRetainedFiles):
    particle: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.particle]

    @property
    def not_retained(self) -> List[Path]:
        return [self.particle]

    @classmethod
    def from_split_particle_files(cls, spf: SplitParticleFiles) -> List[SplitParticleFile]:
        return [SplitParticleFile(pf) for pf in spf.files]


@dataclass
class DethinningOutputFiles(NotAllRetainedFiles):
    dethinned_particle: Path
    stdout: Path
    stderr: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.dethinned_particle, self.stderr, self.stdout]

    @property
    def not_retained(self) -> List[Path]:
        return [self.dethinned_particle]

    @classmethod
    def from_particle_file(cls, pf: SplitParticleFile) -> DethinningOutputFiles:
        dethinning_dir = fileio.dethinning_output_files_dir()
        particle_file_name = pf.particle.name
        return cls(
            dethinned_particle=dethinning_dir / (particle_file_name + '.dethinned'),
            stdout=dethinning_dir / (particle_file_name + '.dethin.stdout'),
            stderr=dethinning_dir / (particle_file_name + '.dethin.stderr'),
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr)
        check_last_line_contains(self.stdout, 'OK')
        check_particle_file_contents(self.dethinned_particle)


@dataclass
class DethinningStep(PipelineStep):
    input_: SplitParticleFile
    output: DethinningOutputFiles

    @classmethod
    def from_particle_file_splitting_step(
        cls, particle_file_splitting: ParticleFileSplittingStep
    ) -> List[DethinningStep]:
        particle_files = SplitParticleFile.from_split_particle_files(particle_file_splitting.output)
        return [
            DethinningStep(
                input_=pf, output=DethinningOutputFiles.from_particle_file(pf), previous_steps=[particle_file_splitting]
            )
            for pf in particle_files
        ]

    @property
    def description(self) -> str:
        return f"Dethinning {self.input_.particle.name}"

    def _run(self):
        run_dethinning(self.input_.particle, self.output.dethinned_particle, self.output.stdout, self.output.stderr)

    def _post_run(self):
        self.input_.delete_not_retained_files()
