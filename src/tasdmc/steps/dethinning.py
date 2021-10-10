from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from wurlitzer import pipes

from typing import List

from tasdmc import fileio
from tasdmc import tasdmc_ext
from .base import Files, FileInFileOutStep
from .particle_file_splitting import SplitParticleFiles, ParticleFileSplittingStep
from .exceptions import FilesCheckFailed
from .utils import check_particle_file_contents


@dataclass
class ParticleFile(Files):
    particle: Path

    @property
    def all(self) -> List[Path]:
        return [self.particle]

    @classmethod
    def from_split_particle_files(cls, spf: SplitParticleFiles) -> List[ParticleFile]:
        return [cls(file) for file in spf.files]

    def _check_contents(self):
        check_particle_file_contents(self.particle)


@dataclass
class DethinningOutputFiles(Files):
    dethinned_particle: Path
    stdout: Path
    stderr: Path

    @property
    def all(self) -> List[Path]:
        return [self.dethinned_particle, self.stderr, self.stdout]

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
        if self.stderr.stat().st_size > 0:
            raise FilesCheckFailed(f"{self.stderr.name} file contains errors")
        with open(self.stdout, 'r') as f:
            for line in f:
                line = line.strip()
            if not (isinstance(line, str) and line.startswith('RUNH: 1') and line.endswith('RUNE: 1')):
                raise FilesCheckFailed(f"Dethinning stdout {self.stdout.name} does not end with RUNH/RUNE line")
        check_particle_file_contents(self.dethinned_particle)


@dataclass
class DethinningStep(FileInFileOutStep):
    input_: ParticleFile
    output: DethinningOutputFiles

    @classmethod
    def from_particle_file_splitting_step(
        cls, particle_file_splitting: ParticleFileSplittingStep
    ) -> List[DethinningStep]:
        particle_files = ParticleFile.from_split_particle_files(particle_file_splitting.output)
        return [cls(input_=pf, output=DethinningOutputFiles.from_particle_file(pf)) for pf in particle_files]

    @property
    def description(self) -> str:
        return f"Dethinning {self.input_.particle.name}"

    def _run(self):
        with open(self.output.stdout, 'w') as stdout_file, open(self.output.stderr, 'w') as stderr_file:
            with pipes(stdout=stdout_file, stderr=stderr_file):
                tasdmc_ext.run_dethinning(str(self.input_.particle), "", str(self.output.dethinned_particle))
