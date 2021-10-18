# `tasdmc` - Telescope Array Surface Detectors Monte Carlo simulation

`tasdmc` aims at providing set of scripts to run Telescope Array Surface Detectors Monte Carlo simulation in a reliable, transparent, configurable and reproducible way.


## Installation

First things first:

```bash
# clone repo
git clone https://github.com/nj-vs-vh/tasdmc.git

# recommended: create virtual environment for the package (with `conda`, `venv`, `virtualenv`, ...)
# example for `venv` (lightweight and provided with python 3 by default):
python -m venv taenv
source taenv/bin/activate

# go to cloned repository dir
cd tasdmc

# install Python dependencies
pip install -r requirements.txt
```

### Prerequisites and external resources

1. `CORSIKA`: must be compiled as usual with `coconut`. Recommended build options: high energy handronic interaction model - QGSJETII-04; low energy - FLUKA; horizontal flat detector array geometry; THINning version (option 2a in v77402); compile and remove temporary files. No automatic building is provided for now, so please keep your builds and `.yaml` config files (see later) in sync manually.
2. [`sdanalysis`](https://github.com/nj-vs-vh/ta-sdanalysis): must be built following README instructions
3. `sdgeant.dst` data file containing pre-computed energy losses inside TA surface detector. It is used as a lookup table for detector response calculation to avoid running expensive Geant4 simulations for each MC run. If it's not present on your system, it can be automatically downloaded at installation, see later.


### Pre-installation configuration

Global configuration is done via environment variables. As usual, their `export`'s may be placed in `.bashrc` or any other activation script.

* `TASDMC_BIN_DIR` controls where C routines will be placed.
* `TASDMC_RUNS_DIR` controls where all the run directories will be created. Note that run directories usually require significant disk space.
* `SDANALYSIS_DIR` points to the `sdanalysis` directory (see prerequisites).
* `TASDMC_MEMORY_PER_PROCESS_GB` specifies memory available per process in Gb. This affects compilation of some C routines (namely, `corsika2geant`) changing allocated array sizes. The choice depends on the system resources, for example on 64 core, 128 Gb RAM machine we would run 64 processes and to utilize all memory we would set this variable to 2.
* `TASDMC_DATA_DIR` points to directory with all data files required for simulation. These include: `sdgeant.dst`, (TBD). If files are missing, they will be downloaded at installation and placed there.

An example of all these variables combined in a single script can be found in [`tasdmc_env.sh`](config_examples/tasdmc_env.sh).

### Finally

```bash
python setup.py install
```

## Usage

`tasdmc` is designed as CLI and configured with human-readable [`.yaml`](https://yaml.org/) files. Note that for each simulation run configuration files are copied to the run directory and are available at any point in the future.

### Run configuration

Run configuration file contains all physical parameters relevant to the simulation (primary particle, energy range, etc) and configuration for (almost) all the simulation steps. See [example](config_examples/run.yaml).
