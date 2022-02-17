pip uninstall tasdmc -y
python setup.py clean
rm -rf build tasdmc.egg-info src/tasdmc.egg-info
python setup.py install

if [ "$1" != "--no-clear" ]; then
    clear
fi

