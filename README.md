# `tasdmc` - Telescope Array Surface Detectors Monte Carlo simulation

`tasdmc` aims at providing set of scripts to run Telescope Array Surface Detectors Monte Carlo
simulation in a reliable, transparent, configurable and reproducible way.


## Installation

First things first:

```bash
# clone repo
git clone https://github.com/nj-vs-vh/tasdmc.git

# recommended: create virtual environment for the package (with `conda`, `venv`, `virtualenv`, ...)
# example for `venv`:
python -m venv taenv
source taenv/bin/activate

# go to cloned repository dir
cd tasdmc

# install Python dependencies
pip install -r requirements.txt
```

### External dependencies

1. `CORSIKA`: must be compiled as usual with `coconut`. Recommended
   build options: high energy handronic interaction model - QGSJETII-04;
   low energy - FLUKA; horizontal flat detector array geometry;
   THINning version (option 2a in v77402); compile and remove temporary files.
   No automatic building is provided for now, so please keep your builds
   and `.yaml` config files (see later) in sync manually.
2. [`sdanalysis`](https://github.com/nj-vs-vh/ta-sdanalysis): must be cloned 
   and built from source following README instructions. Make sure that it is also
   activated (`sdanalysis_env.sh` is sourced) in the same environment `tasdmc`
   is installed in - README contains specific instructions on how to do it.
   > :warning: the linked version of `sdanalysis` is required, older installations may not work!

### Data files

1. `sdgeant.dst` (~145 Mb): contains pre-computed energy losses inside TA surface detector.
   It is used as a lookup table for detector response calculation to avoid running
   expensive Geant4 simulations for each MC run. If it's not present on your system
   (at `$TASDMC_DATA_DIR/sdgeant.dst`), it will be automatically downloaded at installation.
2. `atmos.bin` (~240 Mb): contains atmospheric muon data. If not present, will be downloaded at installation.
3. Calibration files: raw calibration data (`tasdcalib_pass2_YYMMDD.dst`, total of ~104 Gb) should
   be compressed to calibration by epoch (`sdcalib_???.bin`, total of ~33 Gb) ready to be used in
   pipeline. This may be done with [`tasdmc extract-calibration` command](#extract-calibration---create-compressed-calibration-files).


### Pre-installation configuration

Global configuration is done via environment variables. As usual, their `export`'s may
be placed in `.bashrc` or any other activation script.

* `TASDMC_BIN_DIR` controls where compiled C routines will be placed.
* `TASDMC_RUNS_DIR` controls where all the run directories will be created. Note that
  run directories usually require significant amount of disk space.
* `SDANALYSIS_DIR` points to the `sdanalysis` directory (see prerequisites).
* `TASDMC_MEMORY_PER_PROCESS_GB` specifies memory available per process in Gb.
  This affects compilation of some C routines, changing allocated array sizes.
  The choice depends on the system resources, for example on 64 core, 128 Gb RAM
  machine we would run 64 processes and to utilize all memory we would set this
  variable to 2.
* `TASDMC_DATA_DIR` points to directory with all the data files required for simulation,
  see [details](#data-files).

An example of all these variables combined in a single script can be found in
[`tasdmc_env.sh`](config_examples/tasdmc_env.sh). It assumes that it will be copied
to `tasdmc` package dir and contains logic to specify relative paths from there.
For example, use it like this:

```bash
cp config_examples/tasdmc_env.sh .
# edit tasdmc_env.sh if needed, for example point TASDMC_RUNS_DIR to external storage

# then use commands like these
# for user-wide activation in bash
echo "source $(pwd)/tasdmc_env.sh" >> ~/.bashrc
# when using venv
echo "source $(pwd)/tasdmc_env.sh" >> $(python -c "import sys; print(sys.prefix)")/bin/activate
# when using Anaconda
echo "source $(pwd)/tasdmc_env.sh" >> $(python -c "import sys; print(sys.prefix)")/etc/conda/activate.d/activate-tasdmc.sh
```

However, you can `export` these variables any other way you want.

### Finally

```bash
python setup.py install
```

## Usage

`tasdmc` is invoked as a standalone CLI and configured with human-readable
[`.yaml`](https://yaml.org/) files.

### Configuration files

Run configuration file contains all physical parameters relevant to the simulation
(primary particle, energy range, etc) and configuration of (almost) all the simulation
steps. See [example](config_examples/run.yaml) for self-explainatory config example:

```yaml
name: your-run-name
# will be copied here when finalized :)
```


### Commands

##### `run` - start simulation

```bash
tasdmc run --config my-run-config.yaml
```

##### `abort` - abort running simulation

```bash
tasdmc abort my-run-name
```

##### `continue` - continue aborted simulation

```bash
tasdmc continue my-run-name
```

##### `config` - view and update run's configuration

```bash
tasdmc config view my-run-name
tasdmc config update my-run-name -c my-updated-run-config.yaml
```

#### Simulation monitoring commands

##### `progress` - simulation progress

Count how many pipelines are completed, running, pending or failed. A pipeline here
refers to a set of operations on a single CORSIKA input card.

```bash
tasdmc progress my-run-name
```

##### `ps` - simulation processes status

Check whether the run is currently active, list worker processes, print last multiprocessing debug messages.

```bash
tasdmc ps my-run-name -n 5  # to print 5 last log messages from each worker process
```

##### `resources` - simulation resource usage

Check utilization of system resources (CPU, RAM, disk) by run and plot their values change with time

```bash
tasdmc resources my-run-name -p  # -p merges all previous instances of the run into one timeline
```

##### `inputs` - print simulation inputs

```bash
tasdmc inputs my-run-name
```

#### Other commands

##### `extract-calibration` - create compressed calibration files

This command replaces deprecated `sdmc_run_sdmc_calib_extract` script from `sdanalysis`.

```bash
tasdmc extract-calibration -r /full/path/to/raw/calib/data -p 10  # number of processes
```
