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

    log10E_min: float

    @property
    def must_exist(self) -> List[Path]:
        return [self.events]

    @classmethod
    def from_events_file(cls, events_file: EventFiles, log10E_min: float) -> SpectralSampledEvents:
        dir = fileio.spectral_sampled_events_dir()
        datname = events_file.merged_events_file.name.split('.')[0]
        log10E_min_str = str(log10E_min).replace('.', '').ljust(4, '0')
        return SpectralSampledEvents(
            events=dir / f"{datname}.spctr.{log10E_min_str}.dst.gz",
            stdout=dir / f"{datname}.spctr.{log10E_min_str}.stdout",
            stderr=dir / f"{datname}.spctr.{log10E_min_str}.stderr",
            log10E_min=log10E_min,
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=["$$$ dst_get_block_ : End of input file reached"])
        check_last_line_contains(self.stdout, must_contain="OK")


class SpectralSamplingStep(FileInFileOutPipelineStep):
    input_: EventFiles
    output: SpectralSampledEvents

    @property
    def description(self) -> str:
        return (
            f"Spectral sampling events from {self.input_.merged_events_file.name} "
            + f"with E_min=10^{self.output.log10E_min}"
        )

    @classmethod
    def from_events_generation(cls, events_generation_step: EventsGenerationStep) -> List[SpectralSamplingStep]:
        return [
            SpectralSamplingStep(
                events_generation_step.output,
                SpectralSampledEvents.from_events_file(events_generation_step.output, log10E_min),
                previous_steps=[events_generation_step],
            )
            for log10E_min in log10E_mins_from_config()
        ]

    def _run(self):
        run_spectral_sampling(
            self.input_.merged_events_file,
            self.output.events,
            log10E_min=self.output.log10E_min,
            stdout_file=self.output.stdout,
            stderr_file=self.output.stderr,
            target_spectrum=target_spectrum_from_config(),
            dndE_exponent_source=dnde_exponent_from_config(),
        )

    @classmethod
    def validate_config(cls):
        target_spectrum_from_config()
        log10E_mins_from_config()
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


def log10E_mins_from_config() -> List[float]:
    primary_log10E_min = log10E_bounds_from_config()[0]
    aux_log10E_min = list(config.get_key("spectral_sampling.aux_log10E_min", default=[]))
    aux_log10E_min = [float(log10E_min) for log10E_min in aux_log10E_min]
    all_log10E_mins = [primary_log10E_min, *aux_log10E_min]
    assert all(isinstance(log10E, float) for log10E in all_log10E_mins)
    return all_log10E_mins
