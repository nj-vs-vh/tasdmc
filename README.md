![tests](https://github.com/nj-vs-vh/tasdmc/actions/workflows/pull_request.yml/badge.svg)

# `tasdmc` - Telescope Array Surface Detectors Monte Carlo simulation

`tasdmc` aims at providing set of scripts to run Telescope Array Surface Detectors Monte Carlo
simulation in a reliable, transparent, configurable and reproducible way.


## Installation

Installation is done inside `conda` environment (see e.g. [`miniconda`](https://docs.conda.io/en/latest/miniconda.html))
and currently requires building all the C routines from source.

1. Clone the repo
   ```bash
   git clone https://github.com/nj-vs-vh/tasdmc.git
   cd tasdmc
   ```

2. Create and activate `conda` environment
   
   ```bash
   conda create -n ta
   conda activate ta
   ```

3. Run install script. This will prompt you to choose storage directory for `tasdmc` data

   ```bash
   . install.sh
   ```

4. Verify your installation by running
   
   ```bash
   tasdmc --help
   ```

For development, see [manual installation instructions](docs/DEVELOPMENT.md).

### External dependencies

`CORSIKA` must be compiled as usual with `coconut`. Recommended build options: high energy handronic
interaction model - QGSJETII-04; low energy - FLUKA; horizontal flat detector array geometry; THINning
version (option 2a in v77402); compile and remove temporary files. No automatic building is provided
for now, so please keep your builds and config files in sync manually.

### Data files

1. `sdgeant.dst` (~145 Mb): contains pre-computed energy losses inside TA surface detector.
   It is used as a lookup table for detector response calculation to avoid running
   expensive Geant4 simulations for each MC run. If it's not present on your system
   (at `$TASDMC_DATA_DIR/sdgeant.dst`), it can be downloaded with [`tasdmc download-data-files`](#download-data-files---download-data-files-necessary-for-the-simulation).
2. `atmos.bin` (~240 Mb): contains atmospheric muon data, can also be downloaded with 
   [`tasdmc download-data-files`]((#download-data-files---download-data-files-necessary-for-the-simulation)).
3. Calibration files: raw calibration data (`tasdcalib_pass2_YYMMDD.dst`, total of ~104 Gb) should
   be compressed to calibration by epoch (`sdcalib_???.bin`, total of ~33 Gb) ready to be used in
   pipeline. This may be done with [`tasdmc extract-calibration` command](#extract-calibration---create-compressed-calibration-files).


## Usage

`tasdmc` is invoked as a standalone command-line interface  and configured with human-readable
[`.yaml`](https://yaml.org/) files.

### Configuration files

#### `run`

"Run" file contains all physical parameters relevant to the simulation
(primary particle, energy range, etc) and configuration of (almost) all the simulation
steps. See [example](examples/run.yaml):

```yaml
name: your-run-name
description:
  Optional detailed description of run's purpose and other info.

pipeline:
  produce_tawiki_dumps: True  # convert reconstructed .dst.gz files to ASCII tables
                              # in TA Wiki format; defaults to False
  legacy_corsika2geant: False # if set to True, legacy corsika2geant routine with 
                              # appropriate pipeline configuration is used
                              # significantly increases simultaneous disk space
                              # usage; defaults to True for backwards compatibility

input_files:
  particle: proton
  log10E_min: 17.5
  log10E_max: 20.5
  event_number_multiplier: 1.0  # relative to BTS's number of events in each energy bin;
                                # defaults to 1.0

corsika:
  path: full/path/to/corsika/executable
  low_E_hadronic_interactions_model: GHEISHA  # FLUKA | URQMD | GHEISHA
  high_E_hadronic_interactions_model: QGSJETII  # QGSJETII | EPOS
  default_executable_name: True # affects only config validation, set to False when
                                # using non-default executable name; defaults to True

dethinning:
  n_parallel: 6 # determines how many dethinning steps are run in parallel;
                # defaults to the number of CPU on the machine

throwing:  # determines how CORSIKA showers will be 'thrown' to generate MC events
  n_events_at_min_energy: 1e6 # number of events thrown at input_files.log10E_min
  dnde_exponent: 2  # power law spectrum exponent; e.g. 2 means events are thrown
                    # according to dN/dE ~ E^-2
  sdmc_spctr_executable_name: null  # specify this if there are multiple sdmc_spctr
                                    # versions available on your PATH; this should
                                    # not be a problem in most cases and tasdmc will
                                    # check and inform you if this field is needed
  sdmc_spctr_n_try: 10  # retry count for sdmc_sptcr program; defaults to 10
  smear_events_in_bin: True # flag to smear events in 0.1 log energy bin according
                            # to E^-2 spectrum; defaults to True
  calibration_dir: sdcalib_dir_name # directory indise $TASDMC_DATA_DIR containing
                                    # sdcalib_*.bin files, one for each calibration
                                    # epoch; these files can be created from raw
                                    # calibration data with 'extract-calibration'

spectral_sampling:
  target: HiRes # HiRes | TASD2015 | E_minus_3; target spectrum for generated MC events
  aux_log10E_min: # by default spectrum is sampled with log10E_min = input_files.log10E_min,
                  # producing a spectrum with a full range of simulated energies.
                  # for some applications (e.g. neural net training), spectra with higher minimum
                  # energies are useful as the default one will likely contain only a small sample
                  # of high-energy events
    - 18.95
    - 19.45

resources:
  max_processes: 2
  max_memory: 4  # Gb
  # since TASDMC_MEMORY_PER_PROCESS_GB is configured in build-time, only one of these may
  # be specified; if both are specified, the most conservative will be used
  monitor_interval: 60  # sec; null = disable system resources monitoring; defaults to 60

debug:  # all are False/empty by default
  input_hashes: False  # write to input_hashes_debug.log when input hash comparison fails
  file_checks: False  # write to file_checks_debug.log when file check fails
  external_routine_commands: False  # write to routine_cmd_debug.log external routine invocations
  pipelines_mask: []  # limit run only to these DATnnnnnn pipelines
  force_rerun_steps: [] # list of step names that should be rerun regardless of their existing
                        # output files step names here should match class names
                        # (e.g. ReconstructionStep, see full list in tasdmc.steps.__init__.py)

```

#### `nodes`

"Nodes" file contains info on how to distribute run's workload across several SSH-connected nodes.
It contains a list of entries, each describing the node. See [example](examples/nodes.yaml):

```yaml
# Note that auth is not handled by tasdmc: ssh keys must be exchanged beforehand,
# for complex setups ~/.ssh/config file may be used to specify username, proxy jumps etc.
# In short, tasdmc will work only if command like this works in your terminal
# without password prompt and any command line params:
# > ssh worker-machine.url.org
- host: worker-machine.url.org
  conda_env: conda_env_with_tasdmc_installed
  name: node1  # optional name for display purposes
  # overrides "default" values from run.yaml e.g. to specify CORSIKA path for each node
  config_override:
    corsika:
      path: /path/to/corsika/on/worker/machine
    resources:
      max_processes: 4
      max_memory: 12
    # other values will be "inherited" from run.yaml
- host: another-worker-machine.url.org
  conda_env: conda_env_name_on_another_host
  # optional weight determining how much work will be assigned to the node
  # relative to others; defaults to 1.0, so in this case the node will have
  # to do 20% less work
  weight: 0.8
  config_override:
    corsika:
      path: /path/to/corsika/on/another/worker/machine
  # a special host name to create local run on the same machine distributed
  # run is created
- host: self
  weight: 0.1
```

Distributed run functionality aims to be a very light automatization: it just generates configs for each
node's run and starts the simulation on them just as it would be started manually. Hence, you can manually monitor
and control local runs on each node if you prefer. Generated local runs have names according to the convention
`<distributed-run-name>:node-from-<distributed-run-host>`.

### Commands

As usual, `tasdmc` CLI offers built-in help in the form of `tasdmc --help` for command list and overview
and `tasdmc <command> --help` for detailed help on arguments and options.

#### In the beginning was the Word

##### `run-local` - start simulation on this machine

```bash
tasdmc run-local -r my-run-config.yaml

# just to validate that config is OK
tasdmc run-local -r my-run-config.yaml --dry
```

##### `run-distributed` - start simulation on several nodes

```bash
tasdmc run-distributed -r my-run-config.yaml -n my-nodes-config.yaml

# check nodes connectivity and validate config
tasdmc run-distributed -r my-run-config.yaml -n my-nodes-config.yaml --dry
```

#### Monitoring

##### `list` - list runs

```bash
tasdmc list 
```

##### `info` - general info on the run

Among other things, this command prints the entire "run" and "nodes" configs, which is useful
for reproducing the simulation with controllable changes.

```bash
tasdmc info my-run-name
```

##### `status` - simulation runtime status

```bash
tasdmc status my-run-name

# to print a list of current processes spawned for the simulation
tasdmc status my-run-name -p

# to print 5 last log messages indicating what each worker process is doing
tasdmc status my-run-name -n 5
```

##### `progress` - simulation progress overview

A unit of progress is "pipeline" -- consecutive set of operations stemming from a
single CORSIKA simulation. `progress` counts how many pipelines are completed, running,
pending or failed.

```bash
tasdmc progress my-run-name

# to see individual nodes' progresses in distributed run
tasdmc progress my-run-name --per-node
```

##### `resources` - simulation resources usage

If system resources monitoring was enabled in config (it is by default), this will print utilization
of system resources (CPU, RAM, disk) by the simulation.

```bash
tasdmc resources my-run-name
```

##### `inputs` - print simulation inputs log

```bash
tasdmc inputs my-run-name
```

#### Controlling the simulation

##### `abort` - abort running simulation

```bash
tasdmc abort my-run-name
```

##### `continue` - continue aborted simulation

```bash
tasdmc continue my-run-name
```

##### `update-config` - update configuration

Calculates diff between old and new config and checks if the new config is valid.

```bash
tasdmc update-config my-local-run-name -r my-new-run.yaml
tasdmc update-config my-distributed-run-name -r my-new-run.yaml -n my-new-nodes.yaml
```

#### Advanced

##### `inspect` - inspect simulation steps for each pipeline with detailed status

```bash
tasdmc inspect my-run-name --verbose --page 10  # prints detailed reports on all pipelines
tasdmc inspect my-run-name --failed  # only inspects failed pipelines
```

##### `fix-failed`

Most of the time even if pipeline has failed it will just restart failed steps on the next `continue` command.
But in some cases this is not possible, e.g. if previous step's outputs were already deleted for some
reason. This command should be used for such cases.

```bash
tasdmc fix-failed my-run-name  # will perform soft cleanup, deleting only necessary steps
tasdmc fix-failed my-run-name --hard  # will completely wipe all failed pipelines
```

#### Other commands

##### `extract-calibration` - create compressed calibration files

This command replaces deprecated `sdmc_run_sdmc_calib_extract` script from `sdanalysis`.

```bash
tasdmc extract-calibration -r /full/path/to/raw/calib/data -p 10  # number of processes
```

##### `download-data-files` - download data files necessary for the simulation 

```bash
tasdmc download-data-files
```
