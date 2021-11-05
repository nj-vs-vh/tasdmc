# `tasdmc` - Telescope Array Surface Detectors Monte Carlo simulation

`tasdmc` aims at providing set of scripts to run Telescope Array Surface Detectors Monte Carlo
simulation in a reliable, transparent, configurable and reproducible way.


## Installation

Installation is done with `conda` package manager (see e.g. [`miniconda`](https://docs.conda.io/en/latest/miniconda.html)).

Currently no remote channel is configured, use local `tasdmc-?.?.?-py39_0.tar.bz2` archive.

1. Create and activate `conda` environment
   
   ```bash
   conda create -n ta
   conda activate ta
   ```

2. Install the package

   ```bash
   conda install -c conda-forge -c nj-vs-vh tasdmc
   ```

3. Run `tasdmc-init` to configure and finalize the installation. This will prompt you to choose storage directory
   for the package and save it in the activation script. You will have to re-activate your environment after this:

   ```bash
   tasdmc-init
   conda deactivate
   conda activate ta
   ```

4. Verify your installation by running
   
   ```bash
   tasdmc --help
   ```

For non-linux64 systems or development purposes, see [manual installation instructions](docs/MANUAL-INSTALL.md).

### External dependencies

`CORSIKA` must be compiled as usual with `coconut`. Recommended build options: high energy handronic
interaction model - QGSJETII-04; low energy - FLUKA; horizontal flat detector array geometry; THINning
version (option 2a in v77402); compile and remove temporary files. No automatic building is provided
for now, so please keep your builds and `.yaml` config files (see later) in sync manually.

### Data files

1. `sdgeant.dst` (~145 Mb): contains pre-computed energy losses inside TA surface detector.
   It is used as a lookup table for detector response calculation to avoid running
   expensive Geant4 simulations for each MC run. If it's not present on your system
   (at `$TASDMC_DATA_DIR/sdgeant.dst`), it can be downloaded with `tasdmc download-data-files`.
2. `atmos.bin` (~240 Mb): contains atmospheric muon data, can be downloaded with 
   `tasdmc download-data-files`.
3. Calibration files: raw calibration data (`tasdcalib_pass2_YYMMDD.dst`, total of ~104 Gb) should
   be compressed to calibration by epoch (`sdcalib_???.bin`, total of ~33 Gb) ready to be used in
   pipeline. This may be done with [`tasdmc extract-calibration` command](#extract-calibration---create-compressed-calibration-files).


## Usage

`tasdmc` is invoked as a standalone CLI and configured with human-readable
[`.yaml`](https://yaml.org/) files.

### Configuration files

Run configuration file contains all physical parameters relevant to the simulation
(primary particle, energy range, etc) and configuration of (almost) all the simulation
steps. See [example](config-examples/run.yaml) for self-explainatory config example:

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

##### `download-data-files` - download required data files

```bash
tasdmc download-data-files
```
