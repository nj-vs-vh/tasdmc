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
pip --version
while read requirement; do conda install --yes $requirement; done < requirements.txt
pip install -r requirements-git.txt
$PYTHON setup.py install
