"""CORSIKA input files generation

Based on runcorsd-old/gen_infiles_primary.sh
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import getpass

from typing import List, Tuple

from tasdmc import config, fileio, progress
from ..base import Files, FileInFileOutStep
from .corsika_card import (
    CorsikaCard,
    BTS_PAR,
    PARTICLE_ID_BY_NAME,
    LOG10_E_MAX_POSSIBLE,
    LOG10_E_MIN_POSSIBLE,
    LOG10_E_STEP,
)


class NoFiles(Files):
    @property
    def all(self):
        return []


@dataclass
class CorsikaCardFiles(Files):
    files: List[Path]

    @property
    def all(self):
        return self.files


@dataclass
class CorsikaCardsGenerationStep(FileInFileOutStep):
    input_: NoFiles
    output: CorsikaCardFiles

    @classmethod
    def create_and_run(cls) -> CorsikaCardsGenerationStep:
        """For CORSIKA cards generation a set of output files cannot be easily determined in advance.
        Instead, it is done in runtime based on optimal number of cards per energy bin.

        Because of that, instead of instantiate-then-run, use a single class method
        >>> CorsikaInputFilesGeneration.create_and_run()
        """
        instance = cls(NoFiles(), CorsikaCardFiles([]))
        instance.run()  # here corsika input files are added to output.all list
        return instance

    def run(self):
        progress.info("Generating CORSIKA input files")

        particle, particle_id = _particle_id_from_config()
        progress.info(f'Primary particle: {particle} (id {particle_id})')

        log10E_min, log10E_max = _log10E_bounds_from_config()
        progress.info(
            f'Energy scale (log10(E / eV)): {log10E_min:.1f} ... {log10E_max:.1f}, with step {LOG10_E_STEP:.1f}'
        )

        high_E_model = config.get_key('corsika.high_E_hadronic_interactions_model')
        low_E_model = config.get_key('corsika.low_E_hadronic_interactions_model')
        progress.info(f'Hadronic interactions models: {high_E_model}/{low_E_model}')

        event_number_multiplier = _event_number_multiplier_from_config()
        progress.info(f"Event numbers are multiplied by {event_number_multiplier:.2f} in each energy bin")

        # common corsika card parameters
        card = CorsikaCard()
        card.set_USER(getpass.getuser())
        card.set_HOST("chpc")
        card.set_PRMPAR(particle_id)
        card.replace_card("DIRECT", str(fileio.corsika_output_files_dir()) + '/')  # directing .long and particle file

        if high_E_model == 'EPOS':
            card.add_EPOS_CARDS()

        # as noted by Yana Zhezher, CORSIKA fails with this model and default ECUTS
        if low_E_model == 'URQMD':
            card.replace_card("ECUTS", "0.3  0.05  0.00025  0.00025")

        progress.debug('Per-energy bin cards')
        for E_bin_i in range(1 + int((log10E_max - log10E_min) / LOG10_E_STEP)):
            log10E = log10E_min + E_bin_i * LOG10_E_STEP
            card.set_fixed_log10en(log10E)
            params = BTS_PAR[log10E]
            energy_id = int(params[0])
            card.set_THIN(params[1], params[2], params[3])
            card.set_THINH(params[4], params[5])

            cards_count = int(params[6] * event_number_multiplier)

            # NOTE: this limitation is eliminated in the latest corsika
            # NRREXT option may be used, files are then named DATnnnnnnnnn istead of DATnnnnnn
            if not 0 <= cards_count <= 10000:
                raise ValueError(
                    f"Event number multiplier {event_number_multiplier} results in the file index outside [0; 9999] "
                    + f"(event number without multiplication = {params[6]})."
                )

            skipped_cards_count = 0
            for file_index in range(cards_count):
                runnr = file_index * 100 + energy_id
                card.set_RUNNR(runnr)
                card.set_random_seeds()
                card_file = fileio.corsika_input_files_dir() / f"DAT{runnr:06d}.in"
                self.output.files.append(card_file)
                if config.try_to_continue() and card_file.exists():
                    skipped_cards_count += 1
                    continue
                else:
                    with open(card_file, "w") as f:
                        f.write(card.buf + "\n")

            skipped_msg = (
                ''
                if skipped_cards_count == 0
                else (
                    ' (already found in the run dir)'
                    if skipped_cards_count == cards_count
                    else f' ({skipped_cards_count}/{cards_count} of cards already found in the run dir)'
                )
            )
            progress.debug(
                f"PRIMARY {particle_id:d} ENERGY {log10E:.1f} ({energy_id:02d}): "
                + f"{cards_count:d} cards{skipped_msg}",
            )

    @classmethod
    def validate_config(cls):
        _particle_id_from_config()
        _log10E_bounds_from_config()
        _event_number_multiplier_from_config()

        allowed_high_E_models = ('QGSJETII', 'EPOS')
        if config.get_key('corsika.high_E_hadronic_interactions_model') not in allowed_high_E_models:
            raise config.BadConfigValue(
                f"high_E_hadronic_interactions_model must be one of: {', '.join(allowed_high_E_models)}"
            )
        allowed_low_E_models = ('FLUKA', 'URQMD', 'GHEISHA')
        if config.get_key('corsika.low_E_hadronic_interactions_model') not in allowed_low_E_models:
            raise config.BadConfigValue(
                f"low_E_hadronic_interactions_model must be one of: {', '.join(allowed_low_E_models)}"
            )


# config accessors with validation


def _particle_id_from_config() -> Tuple[str, int]:
    particle = config.get_key('input_files.particle')
    try:
        return particle, PARTICLE_ID_BY_NAME[particle]
    except KeyError:
        raise config.BadConfigValue(
            f'Unknown particle "{particle}", must be one of: {", ".join(PARTICLE_ID_BY_NAME.keys())}'
        )


def _log10E_bounds_from_config() -> Tuple[float, float]:
    try:
        log10E_min = round(float(config.get_key('input_files.log10E_min')), ndigits=1)
        log10E_max = round(float(config.get_key('input_files.log10E_max')), ndigits=1)
        assert log10E_max >= log10E_min, "Maximum primary energy cannot be less than minimal"
        for log10E in (log10E_min, log10E_max):
            assert (
                LOG10_E_MIN_POSSIBLE <= log10E <= LOG10_E_MAX_POSSIBLE,
                "Primary energy (both min and max) must be in "
                + f"[10^{LOG10_E_MIN_POSSIBLE:.1f}, 10^{LOG10_E_MAX_POSSIBLE:.1f}] eV",
            )
            assert log10E in BTS_PAR.keys(), f"No known BTS infile generation parameters for log10E = {log10E}"
        return log10E_min, log10E_max
    except (ValueError, AssertionError) as e:
        raise config.BadConfigValue(str(e))


def _event_number_multiplier_from_config() -> float:
    event_number_multiplier = config.get_key('input_files.event_number_multiplier', default=1.0)
    try:
        event_number_multiplier = float(event_number_multiplier)
        assert event_number_multiplier > 0
        return event_number_multiplier
    except (ValueError, AssertionError):
        raise config.BadConfigValue(
            f"Event number multiplier must be non-negative float, but {event_number_multiplier} is specified"
        )
