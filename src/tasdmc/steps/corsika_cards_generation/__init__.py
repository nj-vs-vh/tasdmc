"""CORSIKA input files generation

Based on runcorsd-old/gen_infiles_primary.sh
"""

from __future__ import annotations
from pathlib import Path
import getpass
from math import ceil

from typing import List, Tuple, Generator, Iterable

from tasdmc import config, fileio, logs
from .corsika_card import (
    CorsikaCardData,
    BTS_PAR,
    PARTICLE_ID_BY_NAME,
    LOG10_E_MAX_POSSIBLE,
    LOG10_E_MIN_POSSIBLE,
    LOG10_E_STEP,
)


def generate_corsika_cards() -> List[Path]:
    generated_card_paths: List[Path] = []

    particle, particle_id = _particle_id_from_config()
    logs.cards_generation_info(f'Primary particle: {particle} (id {particle_id})')

    log10E_min, log10E_max = log10E_bounds_from_config()
    logs.cards_generation_info(
        f'Energy scale (log10(E / eV)): {log10E_min:.1f} ... {log10E_max:.1f}, with step {LOG10_E_STEP:.1f}'
    )

    high_E_model = config.get_key('corsika.high_E_hadronic_interactions_model')
    low_E_model = config.get_key('corsika.low_E_hadronic_interactions_model')
    logs.cards_generation_info(f'Hadronic interactions models: {high_E_model}/{low_E_model}')

    event_number_multiplier = _event_number_multiplier_from_config()
    logs.cards_generation_info(
        f"Event numbers are multiplied by {event_number_multiplier:.3f} in each energy bin"
    )

    # common corsika card parameters
    cd = CorsikaCardData()
    cd.set_USER(getpass.getuser())
    cd.set_HOST("chpc")
    cd.set_PRMPAR(particle_id)
    cd.replace_card("DIRECT", str(fileio.corsika_output_files_dir()) + '/')  # directing .long and particle file

    if high_E_model == 'EPOS':
        cd.add_EPOS_CARDS()

    # as noted by Yana Zhezher, CORSIKA fails with this model and default ECUTS
    if low_E_model == 'URQMD':
        cd.replace_card("ECUTS", "0.3  0.05  0.00025  0.00025")

    logs.cards_generation_info('\nCards per energy bin')
    for log10E in log10E_range_from_config():
        cd.set_fixed_log10en(log10E)
        params = BTS_PAR[log10E]
        energy_id = int(params[0])
        cd.set_THIN(params[1], params[2], params[3])
        cd.set_THINH(params[4], params[5])

        cards_count = get_cards_count_at_log10E(log10E)  # a total number of cards
        skipped_cards_count = 0

        def file_index_to_runnr(idx: int, energy_id: int) -> str:
            return f"{idx * 100 + energy_id:06d}"

        for card_index in card_index_range_from_config(cards_count):
            runnr = file_index_to_runnr(card_index, energy_id)
            card_file = fileio.corsika_input_files_dir() / f"DAT{runnr}.in"
            generated_card_paths.append(card_file)
            if card_file.exists():
                skipped_cards_count += 1
                continue
            cd.set_RUNNR(runnr)
            cd.set_random_seeds()
            with open(card_file, "w") as f:
                f.write(cd.buf + "\n")

        skipped_msg = (
            ''
            if skipped_cards_count == 0
            else (
                ' (already found in the run dir)'
                if skipped_cards_count == cards_count
                else f' ({skipped_cards_count}/{cards_count} of cards already found in the run dir)'
            )
        )
        logs.cards_generation_info(
            f"PRIMARY {particle_id:d} ENERGY {log10E:.1f} ({energy_id:02d}): "
            + f"{cards_count:d} cards: "
            + f"DAT{file_index_to_runnr(0, energy_id)} ... DAT{file_index_to_runnr(cards_count - 1, energy_id)}"
            + skipped_msg,
        )

    return generated_card_paths


def validate_config():
    _particle_id_from_config()
    log10E_bounds_from_config()
    _event_number_multiplier_from_config()

    for log10E in log10E_range_from_config():
        get_cards_count_at_log10E(log10E)

    card_index_range_from_config(1000)

    allowed_high_E_models = ('QGSJETII', 'EPOS')
    if config.get_key('corsika.high_E_hadronic_interactions_model') not in allowed_high_E_models:
        raise ValueError(
            f"high_E_hadronic_interactions_model must be one of: {', '.join(allowed_high_E_models)}"
        )
    allowed_low_E_models = ('FLUKA', 'URQMD', 'GHEISHA')
    if config.get_key('corsika.low_E_hadronic_interactions_model') not in allowed_low_E_models:
        raise ValueError(
            f"low_E_hadronic_interactions_model must be one of: {', '.join(allowed_low_E_models)}"
        )


def get_cards_count_at_log10E(log10E: float):
    params = BTS_PAR[log10E]
    event_number_multiplier = _event_number_multiplier_from_config()
    cards_count = int(params[6] * event_number_multiplier)

    # NOTE: this limitation is eliminated in the latest corsika
    # NRREXT option may be used, files are then named DATnnnnnnnnn istead of DATnnnnnn
    if not 0 <= cards_count <= 10000:
        raise ValueError(
            f"Event number multiplier {event_number_multiplier} results in the file index outside [0; 9999] "
            + f"(event number without multiplication = {params[6]})."
        )
    return cards_count


# config accessors with validation


def card_index_range_from_config(cards_count: int) -> Iterable[int]:
    """This function returns range(cards_count) for local runs and for distributed runs returns only """
    input_files_subset_config = config.get_key('input_files.subset', default=None)
    if input_files_subset_config is None:  # i.e. this is local run config, generating all cards
        return range(cards_count)

    all_weights = input_files_subset_config['all_weights']
    this_idx = input_files_subset_config['this_idx']
    weight_sum = sum(all_weights)
    normalized_weights = [w / weight_sum for w in all_weights]
    subset_sizes = [ceil(nw * cards_count) for nw in normalized_weights]
    sum_of_subsets = sum(subset_sizes)
    if sum_of_subsets > cards_count:  # because of rounding up
        max_subset_idx = subset_sizes.index(max(subset_sizes))
        subset_sizes[max_subset_idx] -= (sum_of_subsets - cards_count)
    assert sum(subset_sizes) == cards_count

    subset_bounds = [
        (sum(subset_sizes[:i]), sum(subset_sizes[:i+1]))
        for i in range(len(subset_sizes))
    ]
    return range(*subset_bounds[this_idx])


def _particle_id_from_config() -> Tuple[str, int]:
    particle = config.get_key('input_files.particle')
    try:
        return particle, PARTICLE_ID_BY_NAME[particle]
    except KeyError:
        raise ValueError(
            f'Unknown particle "{particle}", must be one of: {", ".join(PARTICLE_ID_BY_NAME.keys())}'
        )


def log10E_bounds_from_config() -> Tuple[float, float]:
    try:
        log10E_min = round(float(config.get_key('input_files.log10E_min')), ndigits=1)
        log10E_max = round(float(config.get_key('input_files.log10E_max')), ndigits=1)
        assert log10E_max >= log10E_min, "Maximum primary energy cannot be less than minimal"
        for log10E in (log10E_min, log10E_max):
            assert LOG10_E_MIN_POSSIBLE <= log10E <= LOG10_E_MAX_POSSIBLE, (
                "Primary energy (both min and max) must be in "
                + f"[10^{LOG10_E_MIN_POSSIBLE:.1f}, 10^{LOG10_E_MAX_POSSIBLE:.1f}] eV",
            )
            assert log10E in BTS_PAR.keys(), f"No known BTS infile generation parameters for log10E = {log10E}"
        return log10E_min, log10E_max
    except (ValueError, AssertionError) as e:
        raise ValueError(str(e))


def log10E_range_from_config() -> Generator[float, None, None]:
    log10E_min, log10E_max = log10E_bounds_from_config()
    for E_bin_i in range(1 + int((log10E_max - log10E_min) / LOG10_E_STEP)):
        yield log10E_min + E_bin_i * LOG10_E_STEP


def _event_number_multiplier_from_config() -> float:
    event_number_multiplier = config.get_key('input_files.event_number_multiplier', default=1.0)
    try:
        event_number_multiplier = float(event_number_multiplier)
        assert event_number_multiplier > 0
        return event_number_multiplier
    except (ValueError, AssertionError):
        raise ValueError(
            f"Event number multiplier must be non-negative float, but {event_number_multiplier} is specified"
        )
