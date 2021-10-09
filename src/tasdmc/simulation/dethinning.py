from tasdmc import tasdmc_ext

from pathlib import Path


# TODO: add exception handling and output file checks


def split_thinned_corsika_output(particle_file: Path, n_parts_split: int):
    tasdmc_ext.split_thinned_corsika_output(str(particle_file), n_parts_split)


def run_dethinning(particle_file: Path, output_file: Path):
    # running without longtitude file for now
    tasdmc_ext.run_dethinning(str(particle_file), "", str(output_file))
