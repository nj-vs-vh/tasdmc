if [ -z "${CONDA_PREFIX}" ]; then
    echo "tasdmc assumes installation into conda environment! Install conda and run
> conda create -n my-env-name

Aborting"
    return 1
fi

if ! [ -f install.sh ]; then
    echo "install.sh script assumes running from tasdmc directory, please first 'cd' there"
    return 1
fi


function reactivate_conda_env() {
    echo "Reactivating conda environment"
    ENV_NAME=$CONDA_DEFAULT_ENV
    conda deactivate
    conda activate $ENV_NAME
}


echo "
This is tasdmc - Telescope Array Surface Detector Monte Carlo simulation pipeline package

It includes core C programs for various low-level tasks and a Python package
with high-level interface, pipeline management, process and cluster node parallelization, etc.

Refer to https://github.com/nj-vs-vh/tasdmc for documentation and instructions"

echo "
1. Preparing conda environment - installing CERN ROOT and GNU Scientific Library
"
# root is required for building sdanalysis routines but also automatically installs Python, pip etc
conda install -c conda-forge root bz2file gsl -y
if [ $? -ne 0 ]; then
    echo "Command failed, aborting"
    return 1
fi

reactivate_conda_env


echo "
2. Building and installing sdanalysis package
"
source scripts/git_setup_submodule.sh
cd src/sdanalysis
mkdir -p bin
mkdir dst2k-ta/lib -p
export C_INCLUDE_PATH=$CONDA_PREFIX/include:$C_INCLUDE_PATH
export LIBRARY_PATH=$CONDA_PREFIX/lib:$LIBRARY_PATH
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
make
if [ $? -ne 0 ]; then
    echo "Command failed, aborting"
    return 1
fi
cp bin/* $CONDA_PREFIX/bin
cd ../..


echo "
3. Building and installing tasdmc's included C programs
"
export SDANALYSIS_DIR=$(readlink -f ./src/sdanalysis)
source scripts/activation/tasdmc-activate-common.sh
cd src/c_routines
make install
if [ $? -ne 0 ]; then
    echo "Command failed, aborting"
    return 1
fi
cd ../..


echo "
4. Installing Python requirements
"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Command failed, aborting"
    return 1
fi


echo "
5. Installing tasdmc Python package
"
python setup.py install
if [ $? -ne 0 ]; then
    echo "Command failed, aborting"
    return 1
fi


echo "
6. Configuring tasdmc
"
if [ -z "${TASDMC_STORAGE_DIR}" ]; then
    echo "Specify the storage directory. All tasdmc stuff will be placed there.
Note that this directory will occupy a significant amount of disk space (up to hundreds of Gb)
if you plan on running simulations.
"
    read -p '> ' TASDMC_STORAGE_DIR
else
    echo "TASDMC_STORAGE_DIR environment variable found, using it"
fi

TASDMC_STORAGE_DIR=$(readlink -f $TASDMC_STORAGE_DIR)
if [ ! -d $TASDMC_STORAGE_DIR ]; then
    echo "Specified TASDMC_STORAGE_DIR=$TASDMC_STORAGE_DIR do not exist, aborting"
    return 1
fi

TASDMC_DATA_DIR=$TASDMC_STORAGE_DIR/data
TASDMC_RUNS_DIR=$TASDMC_STORAGE_DIR/runs

echo "All of your runs will be placed in
${TASDMC_RUNS_DIR}
All data files must be present in
${TASDMC_DATA_DIR}
"
mkdir -p $TASDMC_RUNS_DIR $TASDMC_DATA_DIR

ACTIVATION_SCRIPTS_DIR=$CONDA_PREFIX/etc/conda/activate.d
mkdir -p $ACTIVATION_SCRIPTS_DIR
ACTIVATION_SCRIPT=$ACTIVATION_SCRIPTS_DIR/tasdmc-activate-configured.sh
echo "export TASDMC_SRC_DIR=$(pwd)" > $ACTIVATION_SCRIPT
echo "export TASDMC_STORAGE_DIR=$TASDMC_STORAGE_DIR" >> $ACTIVATION_SCRIPT
echo "export TASDMC_DATA_DIR=$TASDMC_STORAGE_DIR/data" >> $ACTIVATION_SCRIPT
echo "export TASDMC_RUNS_DIR=$TASDMC_STORAGE_DIR/runs" >> $ACTIVATION_SCRIPT
echo "export SDANALYSIS_DIR=$(pwd)/src/sdanalysis" >> $ACTIVATION_SCRIPT

cp scripts/activation/* $ACTIVATION_SCRIPTS_DIR


reactivate_conda_env
