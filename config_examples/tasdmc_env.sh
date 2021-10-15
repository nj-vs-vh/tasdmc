export TASDMC_LIB_DIR=$(pwd)/lib
export TASDMC_RUNS_DIR=$(pwd)/runs
export DST2K_DIR=$(realpath $(pwd)/../sdanalysis/dst2k-ta)
export TASDMC_MEMORY_PER_PROCESS_GB=2
export TASDMC_SDGEANT_DST=$(pwd)/data/sdgeant.dst

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TASDMC_LIB_DIR:$DST2K_DIR
