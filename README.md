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
pip install .
```

## Usage

`tasdmc` is designed to be run as CLI and allows several commands. But before that, it must be configured.

### Prerequisites

1. CORSIKA: must be compiled following their instructions with `coconut`. Recommended build options: high energy handronic interaction model - QGSJETII-04; low energy - FLUKA; horizontal flat detector array geometry; THINning version (option 2a in v77402); compile and remove temporary files. No automatic building is provided for now, so please keep your builds and `.yaml` config files (see later) in sync manually.
2. TBD...

### Global configuration

Global configuration is done via environment variables. As usual, their `export`'s may be placed in `.bashrc` or any other activation script.

* `TASDMC_LIB_DIR` controls where C extension libraries will be placed. For now `tasdmc` do not install libraries system-wide so this variable must be set, and `LD_LIBRARY_PATH` must be updated to contain it (`export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TASDMC_LIB_DIR`).
* `TASDMC_RUNS_DIR` controls where all the run directories (see later) are created. If not specified, `/current/working/directory/runs` will be created and used.

An example of all these variables combined in a single script can be found in `tasdmc_env.sh`.

### Configuration files

The whole `tasdmc` run configuration is stored in human-readable [`.yaml`](https://yaml.org/) format. The main file `run.yaml` contains all physical parameters relevant to the simulation (primary particle, energy range, etc) and configuration for (almost) all the simulation steps.

Thanks to the `.yaml` format, config files are almost self-explainatory. See `run.yaml` for example.

Note that for each run config is copied to the run directory and is available at any point in the future.
