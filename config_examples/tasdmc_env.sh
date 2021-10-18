TASDMC_DIR=$(dirname $(realpath ${BASH_ARGV[0]}))

export TASDMC_BIN_DIR=$TASDMC_DIR/bin
export TASDMC_RUNS_DIR=$TASDMC_DIR/runs
export SDANALYSIS_DIR=$(realpath $TASDMC_DIR/../sdanalysis)
export TASDMC_MEMORY_PER_PROCESS_GB=2
export TASDMC_SDGEANT_DST=$TASDMC_DIR/data/sdgeant.dst
