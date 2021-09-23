"""
CORSIKA input files generation

Based on runcorsd-old/gen_infiles_primary.sh and corcard.py
"""

from typing import Dict

from tasdmc.config import get_config_key


class InfilesGenerationError(Exception):
    pass


def generate_corsika_input_files(config: Dict):
    verbose = get_config_key(config, 'verbosity.top_level')
    if verbose:
        print("\nGenerating CORSIKA input files\n")

    prefix = 'corsika_input_files'

    # config reading and validation
    particle = get_config_key(config, 'particle', prefix)
    PARTICLE_ID_BY_NAME = {
        'proton': 14,  # CORSIKA particle ID
        'H': 14,
        'helium': 402,
        'He': 402,
        'nitrogen': 1407,
        'N': 1407,
        'iron': 5626,
        'Fe': 5626,
    }
    try:
        particle_id = PARTICLE_ID_BY_NAME[particle]
    except KeyError:
        raise InfilesGenerationError(
            f'Unknown particle "{particle}", must be one of: {", ".join(PARTICLE_ID_BY_NAME.keys())}'
        )
    if verbose:
        print(f'Primary particle: {particle} (id {particle_id})')

    try:
        log10E_min = float(get_config_key(config, 'log10E_min', prefix))
        assert 15.0 <= log10E_min <= 20.6, "Minimum primary energy must be in [10^15, 10^20.6] eV"
        log10E_max = float(get_config_key(config, 'log10E_max', prefix))
        assert 15.0 <= log10E_max <= 20.6, "Maximum primary energy must be in [10^15, 10^20.6] eV"
        log10E_step = float(get_config_key(config, 'log10E_step', prefix))
        assert (
            (log10E_max - log10E_min) / log10E_step > 1,
            "Maximum energy must be at least one step up from minimum on log scale",
        )
    except (ValueError, AssertionError) as e:
        raise InfilesGenerationError(str(e))
    if verbose:
        print(f'Energy scale (log10(E / eV)): {log10E_min:.1f} ... {log10E_max:.1f}, with step {log10E_step:.1f}')
