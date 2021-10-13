from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from wurlitzer import pipes

from typing import List

from tasdmc import fileio, config, tasdmc_ext
from .base import Files, FileInFileOutStep
from .dethinning import DethinningOutputFiles, DethinningStep
from .utils import check_file_is_empty


@dataclass
class C2GInputFiles(Files):
    dethined_files_listing: Path  # list of paths stored in text file, as from ls * > file_list.txt
    dethinned_particle_files: List[Path]
    corsika_event_name: str  # DATnnnnnn common to all files in list

    @property
    def all(self) -> List[Path]:
        return [self.dethined_files_listing, *self.dethinned_particle_files]

    @classmethod
    def from_dethinning_outputs(cls, dethinning_outputs: List[DethinningOutputFiles]) -> C2GInputFiles:
        if len(dethinning_outputs) == 0:
            raise ValueError(f"Cannot create C2GInputFiles from empty list of particle files")
        corsika_event_name = dethinning_outputs[0].dethinned_particle.name.split('.')[0]  # DATnnnnnn
        for pf in dethinning_outputs:
            if not pf.dethinned_particle.match(f'{fileio.dethinning_output_files_dir()}/{corsika_event_name}.*'):
                raise ValueError(
                    "All particle files must be from the same CORSIKA input file, "
                    + f"but {pf.dethinned_particle.name} doesn't match {corsika_event_name}"
                )

        files_list = fileio.dethinning_output_files_dir() / (corsika_event_name + '.dethinned_list')
        with open(files_list, 'w') as f:
            f.writelines([str(do.dethinned_particle) + '\n' for do in dethinning_outputs])
        
        return cls(
            dethined_files_listing=files_list,
            dethinned_particle_files=[do.dethinned_particle for do in dethinning_outputs],
            corsika_event_name=corsika_event_name,
        )


@dataclass
class C2GutputFiles(Files):
    tile: Path
    stdout: Path
    stderr: Path

    @property
    def all(self) -> List[Path]:
        return [self.tile, self.stderr, self.stdout]

    @classmethod
    def from_c2g_input_files(cls, c2g_input: C2GInputFiles) -> C2GutputFiles:
        outdir = fileio.c2g_output_files_dir()
        return cls(
            tile=outdir / (c2g_input.corsika_event_name + '.tile'),
            stdout=outdir / (c2g_input.corsika_event_name + '.c2g.stdout'),
            stderr=outdir / (c2g_input.corsika_event_name + '.c2g.stderr'),
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=[' $$$ '])


class Corsika2GeantStep(FileInFileOutStep):
    input_: C2GInputFiles
    output: C2GutputFiles

    @classmethod
    def from_dethinning_steps(cls, dethinning_steps: List[DethinningStep]) -> Corsika2GeantStep:
        input_ = C2GInputFiles.from_dethinning_outputs([step.output for step in dethinning_steps])
        output = C2GutputFiles.from_c2g_input_files(input_)
        return cls(input_, output)

    @property
    def description(self) -> str:
        return f"Tile file generation for {self.input_.corsika_event_name} event"

    def _run(self):
        with open(self.output.stdout, 'w') as stdout_file, open(self.output.stderr, 'w') as stderr_file:
            with pipes(stdout=stdout_file, stderr=stderr_file):
                tasdmc_ext.run_corsika2geant(
                    str(self.input_.dethined_files_listing),
                    str(config.Global.sdgeant_dst),
                    str(self.output.tile)
                )
                for path in fileio.c2g_output_files_dir().iterdir():
                    if path.match(f"{self.output.tile}.tmp???"):
                        path.unlink()
