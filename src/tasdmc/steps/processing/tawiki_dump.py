from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tasdmc import fileio
from tasdmc.subprocess_utils import execute_routine, Pipes
from tasdmc.steps.utils import check_last_line_contains, log10E2str
from tasdmc.steps.base.step import PipelineStep
from tasdmc.steps.base.files import Files, files_dataclass
from tasdmc.steps.processing.reconstruction import ReconstructedEvents, ReconstructionStep


@files_dataclass
class TawikiDumpFiles(Files):
    dump: Path
    log: Path

    log10E_min: float

    @classmethod
    def from_reconstructed_events(cls, re: ReconstructedEvents) -> TawikiDumpFiles:
        base_name = (re.rufldf_dst.name).removesuffix(".dst.gz")
        return TawikiDumpFiles(
            dump=fileio.reconstruction_dir() / (base_name + '.sdascii'),
            log=fileio.reconstruction_dir() / (base_name + '.sdascii.log'),
            log10E_min=re.log10E_min,
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
                [self.input_.rufldf_dst, "-no_bw", "-f", "-o", self.output.dump, "-emin", E_min, "-tb"],
                *pipes,
                global_=True,
            )
