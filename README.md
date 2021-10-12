# `tasdmc` - Telescope Array Surface Detectors Monte Carlo simulation

`tasdmc` aims at providing set of scripts to run Telescope Array Surface Detectors Monte Carlo simulation in a reliable, transparent, configurable and reproducible way.

## Installation:

```bash
# recommended: create virtual environment for this package
# you can use conda or venv or virtualenv or whatever
# example for venv (lightweight and provided with python 3 by default):
python -m venv taenv
source taenv/bin/activate

# install tasdmc package from source
git clone https://github.com/nj-vs-vh/tasdmc.git
cd tasdmc
source tasdmc_env.sh  # global package configuration, see below
pip install -r requirements.txt
python setup.py install
```

## Installation


### Prerequisites and resources

1. CORSIKA: must be compiled as usual with `coconut`. Recommended build options: high energy handronic interaction model - QGSJETII-04; low energy - FLUKA; horizontal flat detector array geometry; THINning version (option 2a in v77402); compile and remove temporary files. No automatic building is provided for now, so please keep your builds and `.yaml` config files (see later) in sync manually.
2. [sdanalysis](https://github.com/nj-vs-vh/ta-sdanalysis): must be built following README instructions
3. `sdgeant.dst` data file containing **what**? See later.

### Pre-installation configuration

Global configuration is done via environment variables. As usual, their `export`'s may be placed in `.bashrc` or any other activation script.

* `TASDMC_LIB_DIR` controls where C extension libraries will be placed.
* `TASDMC_RUNS_DIR` controls where all the run directories will be created. Note that run directories usually require significant disk space.
* `DST2K_DIR` points to the `sdanalysis/dst2k-ta` directory
* `TASDMC_MEMORY_PER_PROCESS_GB` specifies memory available per process in Gb. This affects compilation of some C routines (namely, `corsika2geant`) changing allocated array sizes. The choice depends on the system resources, for example on 64 core, 128 Gb RAM machine we would run 64 processes and to utilize all memory we would set this variable to 2.
* `TASDMC_SDGEANT_DST` points to `sdgeant.dst` file. If the file doesn't exist, it is downloaded from [Google Drive](https://drive.google.com/file/d/1ZTSrrAg2T8bvIDhPuh2ruVShmubwvTWG/view?usp=sharing) at installation.

Note that `LD_LIBRARY_PATH` should be updated to include `TASDMC_LIB_DIR` and `DST2K_DIR` paths:
```bash
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TASDMC_LIB_DIR:$DST2K_DIR
```

An example of all these variables combined in a single script can be found in `tasdmc_env.sh`.

## Usage

`tasdmc` is designed as CLI and configured with human-readable [`.yaml`](https://yaml.org/) files. Note that for each simulation run configuration files are copied to the run directory and are available at any point in the future.

### Run configuration

Run configuration file contains all physical parameters relevant to the simulation (primary particle, energy range, etc) and configuration for (almost) all the simulation steps.
