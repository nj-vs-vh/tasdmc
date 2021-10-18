from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import run_corsika2geant
from .base import Files, SkippableFileInFileOutStep
from .dethinning import DethinningOutputFiles, DethinningStep
from .utils import check_file_is_empty, concatenate_and_hash


@dataclass
class C2GInputFiles(Files):
    dethinning_outputs: List[DethinningOutputFiles]
    dethinned_files_listing: Path  # list of paths stored in text file, as from ls * > file_list.txt
    corsika_event_name: str  # DATnnnnnn common to all files in list

    @property
    def dethinning_particle_files(self) -> List[Path]:
        return [do.dethinned_particle for do in self.dethinning_outputs]

    @property
    def must_exist(self) -> List[Path]:
        return self.dethinning_particle_files

    def create_listing_file(self):
        with open(self.dethinned_files_listing, 'w') as f:
            f.writelines([str(pf) + '\n' for pf in self.dethinning_particle_files])

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
        return cls(
            dethinned_files_listing=fileio.dethinning_output_files_dir() / (corsika_event_name + '.dethinned_list'),
            dethinning_outputs=dethinning_outputs,
            corsika_event_name=corsika_event_name,
        )

    @property
    def contents_hash(self) -> str:
        dethinning_output_hashes = [do.contents_hash for do in self.dethinning_outputs]
        return concatenate_and_hash(dethinning_output_hashes)


@dataclass
class C2GOutputFiles(Files):
    tile: Path
    stdout: Path
    stderr: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.tile, self.stderr, self.stdout]

    @classmethod
    def from_c2g_input_files(cls, c2g_input: C2GInputFiles) -> C2GOutputFiles:
        outdir = fileio.c2g_output_files_dir()
        return cls(
            tile=outdir / (c2g_input.corsika_event_name + '_gea.dat'),
            stdout=outdir / (c2g_input.corsika_event_name + '.c2g.stdout'),
            stderr=outdir / (c2g_input.corsika_event_name + '.c2g.stderr'),
        )

    def _check_contents(self):
        check_file_is_empty(
            self.stderr,
            ignore_strings=[
                ' $$$ ',
                # because now we use corsika2geant as a library, elosses are loaded only on first invocation
                'eloss_sdgeant: load_elosses: WARNING: energy loss histograms are already loaded',
            ],
        )


class Corsika2GeantStep(SkippableFileInFileOutStep):
    input_: C2GInputFiles
    output: C2GOutputFiles

    @classmethod
    def from_dethinning_steps(cls, dethinning_steps: List[DethinningStep]) -> Corsika2GeantStep:
        input_ = C2GInputFiles.from_dethinning_outputs([step.output for step in dethinning_steps])
        output = C2GOutputFiles.from_c2g_input_files(input_)
        return cls(input_, output)

    @property
    def description(self) -> str:
        return f"Tile file generation for {self.input_.corsika_event_name} event"

    def _run(self):
        self.input_.create_listing_file()
        with open(self.output.stdout, 'w') as stdout_file, open(self.output.stderr, 'w') as stderr_file:
            run_corsika2geant(
                self.input_.dethinned_files_listing,
                self.output.tile,
                stdout=stdout_file,
                stderr=stderr_file,
            )
        for temp_file in fileio.c2g_output_files_dir().glob(f"{self.output.tile.name}.tmp???"):
            temp_file.unlink()
