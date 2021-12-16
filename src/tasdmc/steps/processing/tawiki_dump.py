from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from itertools import chain

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import execute_routine, Pipes
from tasdmc.steps.utils import check_last_line_contains
from ..base import OptionalFiles, PipelineStep
from ..base.files import OptionalFiles
from .reconstruction import ReconstructedEvents, ReconstructionStep


@dataclass
class TawikiDumpFiles(OptionalFiles):
    dump: Path
    log: Path

    @property
    def id_paths(self) -> List[Path]:
        return [self.log]

    @property
    def must_exist(self) -> List[Path]:
        return self.id_paths

    @property
    def optional(self) -> List[Path]:
        return [self.dump]

    @classmethod
    def from_reconstructed_events(cls, re: ReconstructedEvents) -> TawikiDumpFiles:
        base_name = (re.rufldf_dst.name).removesuffix(".dst.gz")
        return TawikiDumpFiles(
            dump=fileio.reconstruction_dir() / (base_name + '.sdascii'),
            log=fileio.reconstruction_dir() / (base_name + '.sdascii.log'),
        )

    def _check_mandatory_files_contents(self):
        check_last_line_contains(self.log, "OK")


@dataclass
class TawikiDumpStep(PipelineStep):
    input_: ReconstructedEvents
    output: TawikiDumpFiles

    @property
    def description(self) -> str:
        return (
            "Dumping reconstruction result in TA Wiki format "
            + f"from {self.input_.rufldf_dst.relative_to(fileio.run_dir())}"
        )

    @classmethod
    def from_reconstruction_step(cls, reconstruction: ReconstructionStep) -> TawikiDumpStep:
        return TawikiDumpStep(
            input_=reconstruction.output,
            output=TawikiDumpFiles.from_reconstructed_events(reconstruction.output),
            previous_steps=[reconstruction],
        )

    def _run(self):
        with open(self.output.log, 'w') as log:
            if not self.input_.is_realized:
                log.write("Not running TA Wiki dump, no reconstructed events found\n\nOK")
                return

            log.write("Running sdascii\n")
            log.flush()
            E_min = 10 ** (self.input_.log10E_min - 18)  # log10E -> EeV
            with Pipes(self.output.log, self.output.log) as pipes:
                execute_routine(
                    'sdascii.run',
                    [self.input_.rufldf_dst, "-no_bw", "-o", self.output.dump, "-emin", E_min],
                    *pipes,
                    global_=True,
                )
            log.write("\n\nOK\n")


# merging


@dataclass
class TawikiDumpFileSet(OptionalFiles):
    tdfs: List[TawikiDumpFiles]

    @property
    def id_paths(self) -> List[Path]:
        return [tdf.log for tdf in self.tdfs]

    @property
    def must_exist(self) -> List[Path]:
        return self.id_paths

    @property
    def optional(self) -> List[Path]:
        return []


@dataclass
class MergedTawikiDump(OptionalFiles):
    merged_dump: Path

    @classmethod
    def new() -> MergedTawikiDump:
        return MergedTawikiDump(fileio.final_dir() / "tawiki_dump.sdascii")


@dataclass
class TawikiDumpsMergeStep(PipelineStep):
    input_: TawikiDumpFileSet
    output: MergedTawikiDump

    @property
    def description(self) -> str:
        return f"Merging all TA Wiki dumps into one file {self.output.merged_dump.relative_to(fileio.run_dir())}"

    @classmethod
    def from_tawiki_dump_steps(cls, steps: List[TawikiDumpStep]) -> TawikiDumpsMergeStep:
        return TawikiDumpsMergeStep(
            input_=TawikiDumpFileSet([s.output for s in steps]),
            output=MergedTawikiDump.new(),
            previous_steps=steps,
        )

    def _run(self):
        with open(self.output.merged_dump, "w") as out:
            for tdf in self.input_.tdfs:
                if not tdf.is_realized:
                    continue
                with open(tdf.dump, "r") as in_:
                    for line in in_:
                        out.write(line + '\n')
