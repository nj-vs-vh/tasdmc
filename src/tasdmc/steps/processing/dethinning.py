from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import run_dethinning

from tasdmc.steps.base import NotAllRetainedFiles, FileInFileOutPipelineStep
from tasdmc.steps.exceptions import FilesCheckFailed
from tasdmc.steps.utils import check_particle_file_contents, check_file_is_empty, check_last_line_contains

from .particle_file_splitting import SplitParticleFiles, ParticleFileSplittingStep


@dataclass
class ParticleFile(NotAllRetainedFiles):
    particle: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.particle]

    @property
    def not_retained(self) -> List[Path]:
        return [self.particle]

    @classmethod
    def from_split_particle_files(cls, spf: SplitParticleFiles) -> List[ParticleFile]:
        return [cls(file) for file in spf.files]

    def _check_contents(self):
        check_particle_file_contents(self.particle)


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
    def from_particle_file(cls, pf: ParticleFile) -> DethinningOutputFiles:
        dethinning_dir = fileio.dethinning_output_files_dir()
        particle_file_name = pf.particle.name
        return cls(
            dethinned_particle=dethinning_dir / (particle_file_name + '.dethinned'),
            stdout=dethinning_dir / (particle_file_name + '.dethin.stdout'),
            stderr=dethinning_dir / (particle_file_name + '.dethin.stderr'),
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr)
        check_last_line_contains(self.stdout, 'RUNH: 1')
        check_particle_file_contents(self.dethinned_particle)


@dataclass
class DethinningStep(FileInFileOutPipelineStep):
    input_: ParticleFile
    output: DethinningOutputFiles

    @classmethod
    def from_particle_file_splitting_step(
        cls, particle_file_splitting: ParticleFileSplittingStep
    ) -> List[DethinningStep]:
        particle_files = ParticleFile.from_split_particle_files(particle_file_splitting.output)
        return [
            DethinningStep(
                input_=pf, output=DethinningOutputFiles.from_particle_file(pf), previous_step=particle_file_splitting
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
