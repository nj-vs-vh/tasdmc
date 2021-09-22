# Telescope Array Surface Detectors Monte Carlo scripts

Based on Ben Stokes' scripts, rewritten in Python for modularity and uniformity.

WIP

Usage:

```bash
# clone repo
git clone https://github.com/nj-vs-vh/tasdmc.git
cd tasdmc

# create python virtual environment with venv or any other tool
python -m venv venv
source venv/bin/activate

# install tasdmc package from source
pip install .

# run example main script
# this uses default config name config.yaml
python main.py

# see config.yaml and create custom config based on it
# run main script with custom config
python main.py -c my-custom-config.yaml
```
