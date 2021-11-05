echo
echo "1. Building and installing sdanalysis subpackage"
echo
cd src/sdanalysis
mkdir -p bin
mkdir dst2k-ta/lib -p
export C_INCLUDE_PATH=$PREFIX/include:$C_INCLUDE_PATH
echo $C_INCLUDE_PATH
make
mv bin/* $PREFIX/bin
cd ../..

echo
echo "2. Building and installing tasdmc C routines"
echo
cd src/c_routines
export SDANALYSIS_DIR=$(readlink -f ../sdanalysis)
export TASDMC_MEMORY_PER_PROCESS_GB=2
export TASDMC_BIN_DIR=$PREFIX/bin
make install
cd ../..

echo
echo "3. Installing Python tasdmc package"
echo
$PYTHON setup.py install

echo
echo "4. Setting up activation scripts and tasdmc-init"
echo
ACTIVATION_SCRIPTS_DIR=$PREFIX/etc/conda/activate.d
mkdir -p $ACTIVATION_SCRIPTS_DIR
cp conda-build-recipe/scripts/tasdmc-autocomplete.sh $ACTIVATION_SCRIPTS_DIR
cp conda-build-recipe/scripts/tasdmc-activate-common.sh $ACTIVATION_SCRIPTS_DIR

TASDMC_INIT_SCRIPT=conda-build-recipe/scripts/tasdmc-init
while read requirement; do echo pip install $requirement --quiet >> $TASDMC_INIT_SCRIPT; done < requirements.txt
chmod -x $TASDMC_INIT_SCRIPT
cp $TASDMC_INIT_SCRIPT $PREFIX/bin
