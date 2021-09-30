"""CORSIKA input files generation

Based on runcorsd-old/gen_infiles_primary.sh and corcard.py
"""

from typing import Dict
import click

from tasdmc.config import get_config_key, get_verbosity
from tasdmc.fileio import corsika_input_files_dir

from .corsika_card import generate_corsika_cards, LOG10_E_STEP, LOG10_E_MIN_POSSIBLE, LOG10_E_MAX_POSSIBLE


class InfilesGenerationError(Exception):
    pass


PARTICLE_ID_BY_NAME = {
    'proton': 14,
    'H': 14,
    'helium': 402,
    'He': 402,
    'nitrogen': 1407,
    'N': 1407,
    'iron': 5626,
    'Fe': 5626,
}


def generate_corsika_input_files(config: Dict):
    verbosity = get_verbosity(config)
    verbose = verbosity > 0

    if verbose:
        click.secho("\nGenerating CORSIKA input files\n", bold=True)

    prefix = 'corsika_input_files'

    particle = get_config_key(config, 'particle', prefix)
    try:
        particle_id = PARTICLE_ID_BY_NAME[particle]
    except KeyError:
        raise InfilesGenerationError(
            f'Unknown particle "{particle}", must be one of: {", ".join(PARTICLE_ID_BY_NAME.keys())}'
        )
    if verbose:
        click.echo(f'Primary particle: {particle} (id {particle_id})')

    try:
        log10E_min = round(float(get_config_key(config, 'log10E_min', prefix)), ndigits=1)
        log10E_max = round(float(get_config_key(config, 'log10E_max', prefix)), ndigits=1)
        assert log10E_max >= log10E_min, "Maximum primary energy cannot be less than minimal"
        for log10E in (log10E_min, log10E_max):
            assert (
                LOG10_E_MIN_POSSIBLE <= log10E <= LOG10_E_MAX_POSSIBLE,
                "Primary energy (both min and max) must be in "
                + f"[10^{LOG10_E_MIN_POSSIBLE:.1f}, 10^{LOG10_E_MAX_POSSIBLE:.1f}] eV"
            )
    except (ValueError, AssertionError) as e:
        raise InfilesGenerationError(str(e))
    if verbose:
        click.echo(f'Energy scale (log10(E / eV)): {log10E_min:.1f} ... {log10E_max:.1f}, with step {LOG10_E_STEP:.1f}')

    high_E_model = get_config_key(config, 'high_E_hadronic_interactions_model', prefix)
    low_E_model = get_config_key(config, 'low_E_hadronic_interactions_model', prefix)
    if verbose:
        click.echo(f'Hadronic interactions models: {low_E_model}/{high_E_model}')

    event_number_multiplier = get_config_key(config, 'event_number_multiplier', prefix, default=1.0)
    try:
        event_number_multiplier = float(event_number_multiplier)
        assert event_number_multiplier > 0
    except (ValueError, AssertionError):
        raise InfilesGenerationError(
            f"Event number multiplier must be non-negative float, but {event_number_multiplier} was passed"
        )
    if verbose and event_number_multiplier != 1.0:
        click.echo(f"Event numbers are multiplied by {event_number_multiplier:.2f} in each energy bin")

    infiles_dir = corsika_input_files_dir(config)
    infiles_dir.mkdir()

    verbose_card_generation = verbosity > 1
    if verbose_card_generation:
        click.echo('')
    for E_bin_i in range(1 + int((log10E_max - log10E_min) / LOG10_E_STEP)):
        generate_corsika_cards(
            primary_particle_id=particle_id,
            log10_E_primary=log10E_min + E_bin_i * LOG10_E_STEP,
            is_epos=(high_E_model == 'EPOS'),
            is_urqmd=(low_E_model == 'URQMD'),
            output_dir=infiles_dir,
            event_number_multiplier=event_number_multiplier,
            verbose=verbose_card_generation,
        )
