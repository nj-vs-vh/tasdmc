if [ "x${BASH_ARGV[0]}" = "x" ]; then
    if [ ! -f ./tasdmc_env.sh ]; then
        echo 'ERROR: must "cd /tasdmc/dir/path" before calling "source tasdmc_env.sh" for this version of bash!'
        return
    fi
    TASDMC_DIR=$(pwd)
else
    TASDMC_DIR=$(dirname ${BASH_ARGV[0]})
fi

export TASDMC_BIN_DIR=$TASDMC_DIR/bin
export TASDMC_RUNS_DIR=$TASDMC_DIR/runs
export SDANALYSIS_DIR=$(readlink $TASDMC_DIR/../sdanalysis)
export TASDMC_MEMORY_PER_PROCESS_GB=2
export TASDMC_DATA_DIR=$TASDMC_DIR/data
