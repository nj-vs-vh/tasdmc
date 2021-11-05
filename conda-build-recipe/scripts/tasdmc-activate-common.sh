# activation script, executed on user system during env activation

# in conda package tasdmc C routines are installed into env's bin
export TASDMC_BIN_DIR=$CONDA_PREFIX/bin
# in conda package tasdmc is build with constant 2 Gb per process memory allocation, see build.sh
export TASDMC_MEMORY_PER_PROCESS_GB=2
