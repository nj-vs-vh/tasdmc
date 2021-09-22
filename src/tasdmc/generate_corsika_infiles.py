"""
CORSIKA input files generation for TA SD Monte Carlo

Based on runcorsd-old/gen_infiles_primary.sh
"""

from typing import Dict

from .config import get_config_key


# CORSIKA particle ID by human-readable name
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


class InfilesGenerationError(Exception):
    pass


def generate_corsika_infiles(config: Dict):
    verbose = get_config_key(config, 'verbosity.top_level')
    if verbose:
        print("\nGenerating CORSIKA input files\n")

    prefix = 'infiles'
    particle = get_config_key(config, 'particle', prefix)
    particle_id = PARTICLE_ID_BY_NAME.get(particle)
    if particle_id is None:
        raise InfilesGenerationError(
            f'Unknown particle "{particle}", expect one of: {", ".join(PARTICLE_ID_BY_NAME.keys())}'
        )
    if verbose:
        print(f'Primary particle: {particle} (id {particle_id})')
