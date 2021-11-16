""".tothrow files specify how many times a given DATnnnnnn_gea.dat file should be used
to generate MC events per calibration epoch (30 days). This number depends on the energy
and target spectrum specified in config

This step replaces deprecated sdmc_prep_sdmc_run script from sdanalysis.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct
import math
import re

from typing import List, Tuple

from tasdmc import config
from tasdmc.steps.base import Files, PipelineStep
from tasdmc.steps.processing.corsika2geant import C2GOutputFiles, Corsika2GeantStep
from tasdmc.steps.corsika_cards_generation import get_cards_count_by_log10E, log10E_bounds_from_config


@dataclass
class TothrowFile(Files):
    tothrow: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.tothrow]

    @classmethod
    def from_corsika2geant_output(cls, c2g_output: C2GOutputFiles):
        return TothrowFile(c2g_output.tile.parent / (c2g_output.tile.name + '.tothrow.txt'))

    def get_showlib_and_nparticles(self) -> Tuple[Path, int]:
        self.assert_files_are_ready()
        with open(self.tothrow, 'r') as f:
            showlib_file = Path(f.readline().strip().replace('SHOWLIB_FILE', '').strip())
            n_particles_per_epoch = int(f.readline().strip().replace('NPARTICLE_PER_EPOCH', '').strip())
        return showlib_file, n_particles_per_epoch


class TothrowGenerationStep(PipelineStep):
    input_: C2GOutputFiles
    output: TothrowFile

    @property
    def description(self) -> str:
        return f"Tothrow files generation for {self.input_.corsika_event_name}"

    @classmethod
    def from_corsika2geant(cls, c2g_step: Corsika2GeantStep) -> TothrowGenerationStep:
        return TothrowGenerationStep(
            c2g_step.output,
            TothrowFile.from_corsika2geant_output(c2g_output=c2g_step.output),
            previous_steps=[c2g_step],
        )

    def _run(self):
        # quick'n'dirty workaround - getting log10E from DATnnnnXX name
        m = re.match(r'DAT\d\d\d\d(?P<energy_id>\d\d)', self.input_.corsika_event_name)
        if m is None:
            raise ValueError(
                f"CORSIKA event name '{self.input_.corsika_event_name}' doesn't match expected pattern 'DATnnnnXX'!"
            )
        energy_id = int(m.group("energy_id"))
        if 0 <= energy_id <= 25:
            log10E = 18.0 + (energy_id - 0) * 0.1
        elif 26 <= energy_id <= 39:
            log10E = 16.6 + (energy_id - 26) * 0.1
        elif 80 <= energy_id <= 85:
            log10E = 16.0 + (energy_id - 80) * 0.1
        else:
            raise ValueError(
                f"CORSIKA event name '{self.input_.corsika_event_name}' contains unknown energy ID: {energy_id}"
            )
        log10E = round(log10E, ndigits=1)

        N0 = _normalizing_constant_from_config()
        dndE_exponent = dnde_exponent_from_config()
        log10E_min, _ = log10E_bounds_from_config()
        dndlogE_exponent = dndE_exponent - 1
        n_particles_in_energy_bin = N0 * 10 ** (-dndlogE_exponent * (log10E - log10E_min))
        n_particles = int(n_particles_in_energy_bin / get_cards_count_by_log10E(log10E))

        # legacy values for backward compatibilty, taken from sdmc_prep_sdmc_run script
        NDWORD = 273  # same as in src/c_routines/corsika2geant/constants.h
        with open(self.input_.tile, "rb") as f:
            eventbuf = struct.unpack(NDWORD * 'f', f.read(NDWORD * 4))
        ptype = int(math.floor(eventbuf[2] + 0.5))
        energy = 9.0 + math.log10(eventbuf[3])  # GeV -> log10(E / eV)
        theta = 180.0 / math.pi * eventbuf[10]  # rad -> deg

        tothrow_contents = (
            f"SHOWLIB_FILE {self.input_.tile}\n"
            + f"NPARTICLE_PER_EPOCH {n_particles}\n"
            + f"PTYPE {ptype:d}\n"
            + f"ENERGY {energy:.2f}\n"
            + f"THETA {theta:.6f}\n"
        )
        with open(self.output.tothrow, 'w') as f:
            f.write(tothrow_contents)

    @classmethod
    def validate_config(self):
        dnde_exponent_from_config()
        _normalizing_constant_from_config()


def dnde_exponent_from_config() -> float:
    return float(config.get_key('throwing.dnde_exponent'))


def _normalizing_constant_from_config() -> float:
    return float(config.get_key('throwing.n_events_at_min_energy'))
