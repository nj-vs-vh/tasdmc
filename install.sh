set -e

if [ -z "${CONDA_PREFIX}" ]; then
    echo "tasdmc assumes installation into conda environment! Install conda and run
> conda create -n my-env-name

Aborting"
    exit 1;
fi


echo "

This is tasdmc - Telescope Array Surface Detector Monte Carlo simulation pipeline package

It includes C routines for various low-level data processing tasks and a Python package
providing high-level interface, pipeline management, parallelization, etc.

See https://github.com/nj-vs-vh/tasdmc for documentation and instructions

"

echo "

1. Preparing conda environment - installing CERN ROOT
"
# root is required for building sdanalysis routines but also automatically installs Python, pip etc
conda install -c conda-forge root -y


echo "

2. Building and installing sdanalysis routines
"
source scripts/git_setup_submodule.sh
cd src/sdanalysis
mkdir -p bin
mkdir dst2k-ta/lib -p
export C_INCLUDE_PATH=$CONDA_PREFIX/include:$C_INCLUDE_PATH
make
cp bin/* $CONDA_PREFIX/bin
cd ../..


echo "

3. Building and installing tasdmc C routines
"
cd src/c_routines
export SDANALYSIS_DIR=$(readlink -f ../sdanalysis)
source script/activation/tasdmc-activate-common.sh
make install
cd ../..


echo "

4. Installing Python requirements
"
pip install -r requirements.txt


echo "

5. Installing tasdmc Python package
"
python setup.py install


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
    exit 1;
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
touch $ACTIVATION_SCRIPT
echo "export TASDMC_DATA_DIR=$TASDMC_STORAGE_DIR/data" >> $ACTIVATION_SCRIPT
echo "export TASDMC_RUNS_DIR=$TASDMC_STORAGE_DIR/runs" >> $ACTIVATION_SCRIPT

cp script/activation/* $ACTIVATION_SCRIPTS_DIR


echo "Reactivate your environment to complete installation:"
echo "> conda deactivate"
echo "> conda activate ${CONDA_DEFAULT_ENV}"
