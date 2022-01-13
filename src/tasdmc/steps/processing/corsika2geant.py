from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from gdown.cached_download import assert_md5sum

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import execute_routine, Pipes
from tasdmc.steps.base import Files, NotAllRetainedFiles, PipelineStep
from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains, check_tile_file_contents
from tasdmc.utils import concatenate_and_hash

from .dethinning import DethinningOutputFiles, DethinningStep


@dataclass
class C2GInputFiles(NotAllRetainedFiles):
    dethinning_outputs: List[DethinningOutputFiles]
    dethinned_files_listing: Path  # list of paths stored in text file, as from ls * > file_list.txt
    corsika_event_name: str  # DATnnnnnn common to all files in list

    @property
    def _dethinned_particle_files(self) -> List[Path]:
        return [do.dethinned_particle for do in self.dethinning_outputs]

    @property
    def must_exist(self) -> List[Path]:
        return self._dethinned_particle_files

    @property
    def not_retained(self) -> List[Path]:
        return self._dethinned_particle_files

    def create_listing_file(self):
        with open(self.dethinned_files_listing, 'w') as f:
            f.writelines([f'{pf}\n' for pf in self._dethinned_particle_files])

    @classmethod
    def from_dethinning_outputs(cls, dethinning_outputs: List[DethinningOutputFiles]) -> C2GInputFiles:
        if len(dethinning_outputs) == 0:
            raise ValueError("Cannot create C2GInputFiles from empty list of particle files")
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
    corsika_event_name: str  # DATnnnnnn common to all files in list

    @property
    def must_exist(self) -> List[Path]:
        return [self.tile, self.stderr, self.stdout]

    @classmethod
    def from_c2g_input_files(cls, c2g_input: C2GInputFiles) -> C2GOutputFiles:
        return cls.from_corsika_event_name(c2g_input.corsika_event_name)

    @classmethod
    def from_corsika_event_name(cls, corsika_event_name: str) -> C2GOutputFiles:
        outdir = fileio.c2g_output_files_dir()
        return cls(
            tile=outdir / (corsika_event_name + '_gea.dat'),
            stdout=outdir / (corsika_event_name + '.c2g.stdout'),
            stderr=outdir / (corsika_event_name + '.c2g.stderr'),
            corsika_event_name=corsika_event_name,
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=['$$$ dst_get_block_ : End of input file reached'])
        check_last_line_contains(self.stdout, 'OK')
        check_tile_file_contents(self.tile)


class Corsika2GeantStep(PipelineStep):
    input_: C2GInputFiles
    output: C2GOutputFiles

    @classmethod
    def from_dethinning_steps(cls, dethinning_steps: List[DethinningStep]) -> Corsika2GeantStep:
        input_ = C2GInputFiles.from_dethinning_outputs([step.output for step in dethinning_steps])
        output = C2GOutputFiles.from_c2g_input_files(input_)
        return Corsika2GeantStep(input_, output, previous_steps=dethinning_steps)

    @property
    def description(self) -> str:
        return f"Tile file generation for shower {self.input_.corsika_event_name}"

    def _run(self):
        self.input_.create_listing_file()
        with Pipes(self.output.stdout, self.output.stderr) as (stdout, stderr):
            execute_routine(
                'corsika2geant.run',
                [self.input_.dethinned_files_listing, fileio.DataFiles.sdgeant, self.output.tile],
                stdout,
                stderr,
            )
        for temp_file in fileio.c2g_output_files_dir().glob(f"{self.output.tile.name}.tmp???"):
            temp_file.unlink()

    def _post_run(self):
        self.input_.delete_not_retained_files()

    @classmethod
    def validate_config(cls):
        _validate_sdgeant()


def _validate_sdgeant():
    assert (
        fileio.DataFiles.sdgeant.exists()
    ), f"{fileio.DataFiles.sdgeant} file not found, use 'tasdmc download-data-files'"
    assert_md5sum(fileio.DataFiles.sdgeant, '0cebc42f86e227e2fb2397dd46d7d981', quiet=True)
