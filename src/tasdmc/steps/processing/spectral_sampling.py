"""Spectral sampling step takes generated events and samples them according to a desired spectrum"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from typing import List

from tasdmc import config, fileio
from tasdmc.steps.base import OptionalFiles, PipelineStep, files_dataclass
from tasdmc.steps.processing.event_generation import EventFiles, EventsGenerationStep

from tasdmc.subprocess_utils import execute_routine, Pipes
from tasdmc.steps.corsika_cards_generation import log10E_bounds_from_config
from tasdmc.steps.processing.tothrow_generation import dnde_exponent_from_config

from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains, check_dst_file_not_empty, log10E2str


@files_dataclass
class SpectralSampledEvents(OptionalFiles):
    events: Path
    stdout: Path
    stderr: Path

    log10E_min: float

    @property
    def must_exist(self) -> List[Path]:
        return [self.stdout, self.stderr]

    @property
    def optional(self) -> List[Path]:
        return [self.events]

    @classmethod
    def from_events_file(cls, events_file: EventFiles, log10E_min: float) -> SpectralSampledEvents:
        dir = fileio.spectral_sampled_events_dir()
        datname = events_file.merged_events_file.name.split('.')[0]
        log10E_min_str = log10E2str(log10E_min)
        return SpectralSampledEvents(
            events=dir / f"{datname}.spctr.{log10E_min_str}.dst.gz",
            stdout=dir / f"{datname}.spctr.{log10E_min_str}.stdout",
            stderr=dir / f"{datname}.spctr.{log10E_min_str}.stderr",
            log10E_min=log10E_min,
        )

    def _check_mandatory_files_contents(self):
        check_file_is_empty(
            self.stderr,
            ignore_strings=["$$$ dst_get_block_ : End of input file reached"],
            include_file_contents_in_error=True,
        )
        check_last_line_contains(self.stdout, must_contain="OK")

    def _check_optional_files_contents(self):
        check_dst_file_not_empty(self.events)


@dataclass
class SpectralSamplingStep(PipelineStep):
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
        with Pipes(self.output.stdout, self.output.stderr) as (stdout, stderr):
            execute_routine(
                'sdmc_conv_e2_to_spctr.run',
                [
                    '-o',
                    self.output.events,
                    '-s',
                    TargetSpectrum.from_config().value,
                    '-g',  # starting index of the MC event library, default 2.000000
                    dnde_exponent_from_config(),
                    '-e',  # minimum energy [EeV](before energy scale correction), default 0.3162 EeV
                    10 ** (self.output.log10E_min - 18),  # log10(E/eV) => EeV
                    self.input_.merged_events_file,
                ],
                stdout,
                stderr,
                global_=True,
            )

    @classmethod
    def validate_config(cls):
        TargetSpectrum.from_config()
        log10E_mins_from_config()
        dnde_exponent_from_config()


class TargetSpectrum(Enum):
    HIRES2008 = 1  # according to PRL 2008 (https://doi.org/10.1103/PhysRevLett.100.101101)
    TASD2015 = 2  # according to ICRC 2015 paper
    E_MINUS_3 = 3  # dN/dE ~ E^-3 power law

    @classmethod
    def from_config(cls) -> TargetSpectrum:
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
