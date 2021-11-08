"""Spectral sampling step takes generated events and samples them according to a desired spectrum"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from typing import List

from tasdmc import config, fileio
from tasdmc.steps.base import Files, FileInFileOutPipelineStep
from tasdmc.steps.processing.event_generation import EventFiles, EventsGenerationStep

from tasdmc.c_routines_wrapper import run_spectral_sampling, TargetSpectrum
from tasdmc.steps.corsika_cards_generation import log10E_bounds_from_config
from tasdmc.steps.processing.tothrow_generation import dnde_exponent_from_config

from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains


@dataclass
class SpectralSampledEvents(Files):
    events: Path
    stdout: Path
    stderr: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.events]

    @classmethod
    def from_events_file(cls, events_file: EventFiles) -> SpectralSampledEvents:
        dir = fileio.spectral_sampled_events_dir()
        datname = events_file.merged_events_file.name.split('.')[0]
        return SpectralSampledEvents(
            events=dir / f"{datname}.spctr.dst.gz",
            stdout=dir / f"{datname}.spctrsampling.stdout",
            stderr=dir / f"{datname}.spctrsampling.stderr",
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=["$$$ dst_get_block_ : End of input file reached"])
        check_last_line_contains(self.stdout, must_contain="OK")


class SpectralSamplingStep(FileInFileOutPipelineStep):
    input_: EventFiles
    output: SpectralSampledEvents

    @property
    def description(self) -> str:
        return f"Spectral sampling {self.input_.merged_events_file.name}"

    @classmethod
    def from_events_generation(cls, events_generation_step: EventsGenerationStep) -> SpectralSamplingStep:
        return SpectralSamplingStep(
            events_generation_step.output,
            SpectralSampledEvents.from_events_file(events_generation_step.output),
            previous_steps=[events_generation_step],
        )

    def _run(self):
        run_spectral_sampling(
            self.input_.merged_events_file,
            self.output.events,
            target_spectrum=target_spectrum_from_config(),
            log10E_min=log10E_bounds_from_config()[0] - (0.1 / 2),
            dndE_exponent_source=dnde_exponent_from_config(),
            stdout_file=self.output.stdout,
            stderr_file=self.output.stderr,
        )

    @classmethod
    def validate_config(cls):
        target_spectrum_from_config()
        log10E_bounds_from_config()
        dnde_exponent_from_config()


def target_spectrum_from_config() -> TargetSpectrum:
    target_spectrum_str = config.get_key("spectral_sampling.target")
    matching_target_spectra = []
    for ts in TargetSpectrum:
        if ts.name.lower().startswith(target_spectrum_str.lower()):
            matching_target_spectra.append(ts)
    if len(matching_target_spectra) != 1:
        ts_options_str = '\n'.join([ts.name for ts in TargetSpectrum])
        raise ValueError(
            f"Can't find unique target spectrum matching '{target_spectrum_str}', options:\n{ts_options_str}"
        )
    else:
        return matching_target_spectra[0]
