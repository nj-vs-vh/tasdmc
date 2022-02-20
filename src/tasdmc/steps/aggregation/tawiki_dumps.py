from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tasdmc import fileio
from tasdmc.steps.utils import log10E2str
from tasdmc.steps.base.step import PipelineStep
from tasdmc.steps.base.files import Files, files_dataclass
from tasdmc.steps.processing.tawiki_dump import TawikiDumpFiles, TawikiDumpStep

from itertools import chain
from typing import List


@files_dataclass
class TawikiDumpFileSet(Files):
    tdfs: List[TawikiDumpFiles]

    @property
    def all_files(self) -> List[Path]:  # for Files hashing and identification purposes
        return chain.from_iterable((tdf.log, tdf.dump) for tdf in self.tdfs)


@files_dataclass
class MergedTawikiDump(Files):
    merged_dump: Path
    log: Path

    @classmethod
    def new(cls, log10E_min: float) -> MergedTawikiDump:
        dump = fileio.final_dir() / f"tawiki_dump.{log10E2str(log10E_min)}.sdascii"
        return MergedTawikiDump(
            merged_dump=dump,
            log=Path(str(dump) + ".log"),
        )


@dataclass
class TawikiDumpsMergeStep(PipelineStep):
    input_: TawikiDumpFileSet
    output: MergedTawikiDump

    @property
    def description(self) -> str:
        return f"Merging TA Wiki dumps into {self.output.merged_dump.relative_to(fileio.run_dir())}"

    @classmethod
    def from_tawiki_dump_steps(cls, steps: List[TawikiDumpStep], log10E_min: float) -> TawikiDumpsMergeStep:
        return TawikiDumpsMergeStep(
            input_=TawikiDumpFileSet([s.output for s in steps]),
            output=MergedTawikiDump.new(log10E_min),
            previous_steps=steps,
        )

    def _run(self):
        with open(self.output.merged_dump, "w") as out, open(self.output.log, "w") as log:
            for tdf in self.input_.tdfs:
                line_count = 0
                with open(tdf.dump, "r") as in_:
                    for line in in_:
                        line = line.strip()
                        if line:
                            line_count += 1
                            out.write(line + '\n')
                log.write(f"{tdf.dump.relative_to(fileio.run_dir())} - {line_count}\n")
