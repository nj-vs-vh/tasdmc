from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from itertools import chain

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import execute_routine, Pipes
from tasdmc.steps.utils import check_last_line_contains
from ..base.step import PipelineStep
from ..base.files import OptionalFiles, Files
from .reconstruction import ReconstructedEvents, ReconstructionStep


@dataclass
class TawikiDumpFiles(Files):
    dump: Path
    log: Path

    @property
    def must_exist(self) -> List[Path]:
        return self.id_paths

    @classmethod
    def from_reconstructed_events(cls, re: ReconstructedEvents) -> TawikiDumpFiles:
        base_name = (re.rufldf_dst.name).removesuffix(".dst.gz")
        return TawikiDumpFiles(
            dump=fileio.reconstruction_dir() / (base_name + '.sdascii'),
            log=fileio.reconstruction_dir() / (base_name + '.sdascii.log'),
        )

    def _check_contents(self):
        check_last_line_contains(self.log, "Done")


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
        self.output.dump.touch()  # empty text file for dump is OK even if no event will be written there
        if not self.input_.is_realized:
            self.output.log.write_text("Not running TA Wiki dump because no events were reconstructed\n\nDone")
            return

        # E_min = 10 ** (self.input_.log10E_min - 18)  # log10E -> EeV
        
        # using constant default energy cutoff of 1 EeV
        # TODO: create a config field for all the cuts and use it throughout
        E_min = 1.0
        with Pipes(self.output.log, self.output.log) as pipes:
            execute_routine(
                'sdascii.run',
                [self.input_.rufldf_dst, "-no_bw", "-o", self.output.dump, "-emin", E_min],
                *pipes,
                global_=True,
            )


# merging dumps 
# it's a bit hacky
# TODO: create an aggregation step abstraction


@dataclass
class TawikiDumpFileSet(Files):
    tdfs: List[TawikiDumpFiles]

    @property
    def id_paths(self) -> List[Path]:
        return chain.from_iterable((tdf.log, tdf.dump) for tdf in self.tdfs)

    @property
    def must_exist(self) -> List[Path]:
        return self.id_paths


@dataclass
class MergedTawikiDump(Files):
    merged_dump: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.merged_dump]

    @classmethod
    def new(cls) -> MergedTawikiDump:
        return MergedTawikiDump(fileio.final_dir() / "tawiki_dump.sdascii")


@dataclass
class TawikiDumpsMergeStep(PipelineStep):
    input_: TawikiDumpFileSet
    output: MergedTawikiDump

    @property
    def description(self) -> str:
        return f"Merging all TA Wiki dumps into {self.output.merged_dump.relative_to(fileio.run_dir())}"

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
                with open(tdf.dump, "r") as in_:
                    for line in in_:
                        line = line.strip()
                        if line:
                            out.write(line + '\n')
