if [ -z "${TASDMC_STORAGE_DIR}" ]; then
    echo "TASDMC_STORAGE_DIR is not set, aborting installation";
    exit 1;
fi


# creating activation scripts based on supplied env var
ACTIVATION_SCRIPTS_DIR=$CONDA_PREFIX/etc/conda/activate.d
mkdir -p $ACTIVATION_SCRIPTS_DIR
ACTIVATION_SCRIPT=$ACTIVATION_SCRIPTS_DIR/tasdmc-activate.sh
touch $ACTIVATION_SCRIPT
echo "export TASDMC_DATA_DIR=$TASDMC_STORAGE_DIR/data" >> $ACTIVATION_SCRIPT
echo "export TASDMC_RUNS_DIR=$TASDMC_STORAGE_DIR/runs" >> $ACTIVATION_SCRIPT
echo "export TASDMC_BIN_DIR=$CONDA_PREFIX/bin" >> $ACTIVATION_SCRIPT
echo "export TASDMC_MEMORY_PER_PROCESS_GB=2" >> $ACTIVATION_SCRIPT
