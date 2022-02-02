from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.subprocess_utils import execute_routine, Pipes
from tasdmc.steps.base import NotAllRetainedFiles, PipelineStep, files_dataclass
from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains
from tasdmc.utils import concatenate_and_hash

from .dethinning import DethinningOutputFiles, DethinningStep
from .corsika2geant import C2GOutputFiles, _validate_sdgeant


# process separate dethinned particle files and produce partial files


@files_dataclass
class PartialTileFile(NotAllRetainedFiles):
    partial_tile: Path
    stdout: Path
    stderr: Path

    corsika_event_name: str

    @property
    def not_retained(self) -> List[Path]:
        return [self.partial_tile]

    @classmethod
    def from_dethinning_output(cls, dethinning_output: DethinningOutputFiles) -> PartialTileFile:
        corsika_event_name = dethinning_output.dethinned_particle.name.split('.')[0]  # DATnnnnnn
        ptile = str(fileio.c2g_output_files_dir() / (dethinning_output.dethinned_particle.name + '.partial_tile'))
        return PartialTileFile(
            partial_tile=Path(ptile),
            stdout=Path(ptile + '.stdout'),
            stderr=Path(ptile + '.stderr'),
            corsika_event_name=corsika_event_name,
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=['$$$ dst_get_block_ : End of input file reached'])
        check_last_line_contains(self.stdout, 'OK')


@dataclass
class Corsika2GeantParallelProcessStep(PipelineStep):
    input_: DethinningOutputFiles
    output: PartialTileFile

    @classmethod
    def from_dethinning_step(cls, dethinning: DethinningStep) -> Corsika2GeantParallelProcessStep:
        return Corsika2GeantParallelProcessStep(
            input_=dethinning.output,
            output=PartialTileFile.from_dethinning_output(dethinning.output),
            previous_steps=[dethinning],
        )

    @property
    def description(self) -> str:
        return f"Partial tile file generation from {self.input_.dethinned_particle.name}"

    def _run(self):
        with Pipes(self.output.stdout, self.output.stderr) as (stdout, stderr):
            execute_routine(
                'corsika2geant_parallel_process.run',
                [self.input_.dethinned_particle, fileio.DataFiles.sdgeant, self.output.partial_tile],
                stdout,
                stderr,
            )

    def _post_run(self):
        self.input_.delete_not_retained_files()

    @classmethod
    def validate_config(cls):
        _validate_sdgeant()


# merge partial tile files into one final tile


@files_dataclass
class PartialTileFileSet(NotAllRetainedFiles):
    partial_tile_files: List[PartialTileFile]
    listing: Path
    corsika_event_name: str

    @property
    def all_files(self) -> List[Path]:
        # listing can be generated anytime
        return [ptf.partial_tile for ptf in self.partial_tile_files]

    @property
    def not_retained(self) -> List[Path]:
        return self.all_files

    def create_listing_file(self):
        with open(self.listing, 'w') as f:
            f.writelines([f'{ptf.partial_tile}\n' for ptf in self.partial_tile_files])

    @classmethod
    def from_partial_tile_files(cls, ptfs: List[PartialTileFile]) -> PartialTileFileSet:
        if len(ptfs) == 0:
            raise ValueError("Cannot create PartialTileFileSet from empty list of PartialTileFile objects")
        corsika_event_name = ptfs[0].corsika_event_name
        return PartialTileFileSet(
            ptfs,
            listing=fileio.c2g_output_files_dir() / (corsika_event_name + ".partial_tiles_list"),
            corsika_event_name=corsika_event_name,
        )

    def _check_contents(self):
        for ptf in self.partial_tile_files:
            ptf._check_contents()

    @property
    def contents_hash(self) -> str:
        dethinning_output_hashes = [ptf.contents_hash for ptf in self.partial_tile_files]
        return concatenate_and_hash(dethinning_output_hashes)


@dataclass
class Corsika2GeantParallelMergeStep(PipelineStep):
    input_: PartialTileFileSet
    output: C2GOutputFiles

    @classmethod
    def from_c2g_parallel_process_steps(
        cls, c2g_p_process_steps: List[Corsika2GeantParallelProcessStep]
    ) -> Corsika2GeantParallelMergeStep:
        input_ = PartialTileFileSet.from_partial_tile_files([step.output for step in c2g_p_process_steps])
        return Corsika2GeantParallelMergeStep(
            input_=input_,
            output=C2GOutputFiles.from_corsika_event_name(input_.corsika_event_name),
            previous_steps=c2g_p_process_steps,
        )

    @property
    def description(self) -> str:
        return f"Merging partial tile files into final tile for {self.input_.corsika_event_name}"

    def _run(self):
        self.input_.create_listing_file()
        with Pipes(self.output.stdout, self.output.stderr) as (stdout, stderr):
            execute_routine(
                'corsika2geant_parallel_merge.run',
                [self.input_.listing, self.output.tile],
                stdout,
                stderr,
            )
        self.input_.listing.unlink()

    def _post_run(self):
        self.input_.delete_not_retained_files()
