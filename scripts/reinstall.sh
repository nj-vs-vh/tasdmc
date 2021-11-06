pip uninstall tasdmc -y
python setup.py clean
rm -rf build tasdmc.egg-info src/tasdmc.egg-info
python setup.py install
