from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tarfile

from tasdmc import fileio
from tasdmc.steps.base.step import PipelineStep
from tasdmc.steps.base.files import Files, files_dataclass
from tasdmc.steps.utils import log10E2str, check_last_line_contains
from tasdmc.steps.processing.reconstruction import ReconstructedEvents, ReconstructionStep

from typing import List


@files_dataclass
class ReconstructedEventFilesSet(Files):
    reconstructed_event_files: List[ReconstructedEvents]

    @property
    def all_files(self) -> List[Path]:  # for Files hashing and identification purposes
        return [re.log for re in self.reconstructed_event_files]


@files_dataclass
class ReconstructedEventFilesArchive(Files):
    tar: Path
    log: Path

    @classmethod
    def new(cls, log10E_min: float) -> ReconstructedEventFilesArchive:
        dump = fileio.final_dir() / f"reconstructed_events.{log10E2str(log10E_min)}.tar.gz"
        return ReconstructedEventFilesArchive(
            tar=dump,
            log=Path(str(dump) + ".log"),
        )

    def _check_contents(self):
        check_last_line_contains(self.log, "OK")


@dataclass
class ReconstructedEventsArchivingStep(PipelineStep):
    input_: ReconstructedEventFilesSet
    output: ReconstructedEventFilesArchive

    @property
    def description(self) -> str:
        return f"Archiving rufldf.dst.gz files into {self.output.tar.relative_to(fileio.run_dir())}"

    @classmethod
    def from_reconstruction_steps(cls, steps: List[ReconstructionStep], log10E_min: float) -> ReconstructedEventsArchivingStep:
        return ReconstructedEventsArchivingStep(
            input_=ReconstructedEventFilesSet([reco_step.output for reco_step in steps]),
            output=ReconstructedEventFilesArchive.new(log10E_min),
            previous_steps=steps,
        )

    def _run(self):
        realized_dsts = 0
        not_realized_dsts = 0
        with tarfile.open(self.output.tar, "w:gz") as tar, open(self.output.log, "w") as log:
            for reconstructed_events_dst in self.input_.reconstructed_event_files:
                if not reconstructed_events_dst.is_realized:
                    not_realized_dsts += 1
                else:
                    reco_events_path = reconstructed_events_dst.rufldf_dst
                    tar.add(reco_events_path, arcname=reco_events_path.name)
                    realized_dsts += 1
            log.write(f"Added recontructed events files in the archive: {realized_dsts}\n")
            log.write(f"Non-existent files (i.e. no events produced from the shower): {not_realized_dsts}\n")
            log.write("\nOK\n")
