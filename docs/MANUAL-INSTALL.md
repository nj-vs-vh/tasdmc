# Manual `tasdmc` installation

Installation is most commonly and conveniently done with `conda` package manager and a pre-build
linux-64 conda package. But to install on other systems and/or develop the tool, manual installation
is required.

1. Create a virtual environment. All Python packages will be installed there, all binaries will be
   compiled and stored locally. No system- or user-wide changes will be made. For example, using the
   lightweight `venv` tool:

   ```bash
   python -m venv taenv
   source taenv/bin/activate
   ```

2. Build [`sdanalysis`](https://github.com/nj-vs-vh/ta-sdanalysis) as described in README. Make sure
   to add its activation script to `taenv/bin/activate` script:

   ```bash
   cd src/sdanalysis
   echo "source $(pwd)/sdanalysis_env.sh" >> $(python -c "import sys; print(sys.prefix)")/bin/activate
   ```

3. You must define `tasdmc` environment variables:
   * `TASDMC_DATA_DIR` and `TASDMC_RUNS_DIR` have the same meaning as in regular installation
   * `TASDMC_BIN_DIR` controls where compiled C routines will be placed.
   * `SDANALYSIS_DIR` points to the `sdanalysis` directory.
   * `TASDMC_MEMORY_PER_PROCESS_GB` specifies memory available per process in Gb.
     This affects compilation of some C routines, changing allocated array sizes.
     The choice depends on the system resources, for example on 64 core, 128 Gb RAM
     machine we would run 64 processes and to utilize all memory we would set this
     variable to 2.

   An example of all these variables combined in a single script can be found in
   [`tasdmc_env.sh`](config_examples/tasdmc_env.sh). It assumes that it will be copied
   to `tasdmc` package dir and contains logic to specify relative paths from there.
   For example, use it like this:

   ```bash
   cp config-examples/tasdmc_env.sh .
   # edit tasdmc_env.sh if needed, for example point TASDMC_RUNS_DIR to external storage
   echo "source $(pwd)/tasdmc_env.sh" >> $(python -c "import sys; print(sys.prefix)")/bin/activate
   ```

4. Build `tasdmc` C routines with
   
   ```bash
   cd src/c_routines
   make install
   cd ../..
   ```

5. Install Python requirements with
   
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-git.txt
   ```

6. Install `tasdmc` Python package with
   
   ```bash
   python setup.py install
   ```

7. Now `tasdmc` executable should be available in your virtual environment.
   You can check it with `tasdmc --help`
