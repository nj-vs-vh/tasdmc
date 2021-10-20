from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import run_dethinning

from tasdmc.steps.base import NotAllRetainedFiles, FileInFileOutPipelineStep
from tasdmc.steps.exceptions import FilesCheckFailed
from tasdmc.steps.utils import check_particle_file_contents, check_file_is_empty

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
        with open(self.stdout, 'r') as f:
            for line in f:
                line = line.strip()
            if not (isinstance(line, str) and line.startswith('RUNH: 1') and line.endswith('RUNE: 1')):
                raise FilesCheckFailed(f"Dethinning stdout {self.stdout.name} does not end with RUNH/RUNE line")
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
        with open(self.output.stdout, 'w') as stdout_file, open(self.output.stderr, 'w') as stderr_file:
            run_dethinning(self.input_.particle, self.output.dethinned_particle, stdout=stdout_file, stderr=stderr_file)
