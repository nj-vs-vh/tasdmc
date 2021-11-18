from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.c_routines_wrapper import execute_routine, Pipes
from tasdmc.steps.utils import check_last_line_contains, check_dst_file_not_empty
from ..base import OptionalFiles, PipelineStep
from .spectral_sampling import SpectralSampledEvents, SpectralSamplingStep


@dataclass
class ReconstructedEvents(OptionalFiles):
    log: Path

    rufptn_dst: Path
    rufptn_log: Path

    sdtrgbk_dst: Path
    sdtrgbk_log: Path

    rufldf_dst: Path
    rufldf_log: Path

    @property
    def id_paths(self) -> List[Path]:
        return [self.log]

    @property
    def must_exist(self) -> List[Path]:
        return self.id_paths

    @property
    def optional(self) -> List[Path]:
        return [self.rufptn_dst, self.rufptn_log, self.sdtrgbk_dst, self.sdtrgbk_log, self.rufldf_dst, self.rufldf_log]

    @classmethod
    def from_spectral_sampled_events(cls, sse: SpectralSampledEvents) -> ReconstructedEvents:
        datname = sse.events.name.split('.')[0]
        base_name = ''.join([datname, *[suff for suff in sse.events.suffixes if suff not in {'.dst', '.gz'}]])
        dir = fileio.reconstruction_dir()
        return ReconstructedEvents(
            log=dir / (base_name + ".log"),
            rufptn_dst=dir / (base_name + ".rufptn.dst.gz"),
            rufptn_log=dir / (base_name + ".rufptn.log"),
            sdtrgbk_dst=dir / (base_name + '.sdtrgbk.dst.gz'),
            sdtrgbk_log=dir / (base_name + '.sdtrgbk.log'),
            rufldf_dst=dir / (base_name + ".rufldf.dst.gz"),
            rufldf_log=dir / (base_name + ".rufldf.log"),
        )

    def _check_mandatory_files_contents(self):
        check_last_line_contains(self.log, "OK")


@dataclass
class ReconstructionStep(PipelineStep):
    input_: SpectralSampledEvents
    output: ReconstructedEvents

    @property
    def description(self) -> str:
        return f"Reconstruction of {self.input_.events.name}"

    @classmethod
    def from_spectral_sampling(cls, spectral_sampling: SpectralSamplingStep) -> ReconstructionStep:
        return ReconstructionStep(
            input_=spectral_sampling.output,
            output=ReconstructedEvents.from_spectral_sampled_events(spectral_sampling.output),
            previous_steps=[spectral_sampling],
        )

    def _run(self):
        if not self.input_.is_realized:
            self.output.log.write_text("Not running the step, previous step produced empty output\n\nOK")

        with open(self.output.log, 'w') as log:
            log.write("Running rufptn\n")
            with Pipes(self.output.rufptn_log) as stdouterr:
                execute_routine(
                    'rufptn.run',
                    [self.input_.events, "-o1f", self.output.rufptn_dst, "-v", 2],
                    *stdouterr,
                    global_=True,
                )
            check_dst_file_not_empty(self.output.rufptn_dst)

            with Pipes(self.output.sdtrgbk_log) as stdouterr:
                execute_routine(
                    'sdtrgbk.run',
                    [self.output.rufptn_dst, "-o1f", self.output.sdtrgbk_dst],
                    *stdouterr,
                    global_=True,
                )
            check_dst_file_not_empty(self.output.sdtrgbk_dst)

            with Pipes(self.output.rufldf_log) as stdouterr:
                execute_routine(
                    'rufldf.run',
                    [self.output.sdtrgbk_dst, "-o1f", self.output.rufldf_dst],
                    *stdouterr,
                    global_=True,
                )
            check_dst_file_not_empty(self.output.rufldf_dst)
