from tasdmc import tasdmc_ext

from pathlib import Path


def split_thinned_corsika_output(particle_file: Path, n_parts_split: int):
    tasdmc_ext.split_thinned_corsika_output(str(particle_file), n_parts_split)
