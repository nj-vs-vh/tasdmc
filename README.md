# `tasdmc` - Telescope Array Surface Detectors Monte Carlo simulation

`tasdmc` aims at providing set of scripts to run Telescope Array Surface Detectors Monte Carlo simulation in a reliable, transparent, configurable and reproducible way.

## Installation:

```bash
# clone repo
git clone https://github.com/nj-vs-vh/tasdmc.git
cd tasdmc

# create python virtual environment with venv or any other tool
python -m venv venv
source venv/bin/activate

# install tasdmc package from source
pip install .
```

## Usage

`tasdmc` is designed as CLI and allows several commands. But before the `tasdmc` is run, it must be configured.

### Configuration files

All configuration files are stored in human-readable [`.yaml`](https://yaml.org/) format. The main config file is `run.yaml`, which contains all physical parameters relevant to the simulation (primary particle, energy range, etc).

Top-level keys:
* `name` - name of the run, should be unique to avoid confusion. All files relevant to the run will be placed in the directory with this name.
* `corsika_input_files` - controls generation of CORSIKA input
* TBD...

### Global configuration

Besides per-run configs there are some global options controlled with environment variables:

* `TASDMC_RUNS_DIR` controls where all the run directories are created. If not specified, `runs` directory will be created in the current working directory and used to store all the individual runs.
