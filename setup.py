from setuptools import setup, find_packages
from setuptools.command.install import install
from distutils.command.clean import clean

import subprocess
import os
from pathlib import Path


for required_env_var in ('TASDMC_BIN_DIR', 'SDANALYSIS_DIR', 'TASDMC_MEMORY_PER_PROCESS_GB', 'TASDMC_DATA_DIR'):
    if required_env_var not in os.environ:
        raise EnvironmentError(f"{required_env_var} environment variable is not set")

PACKAGE_ROOT = Path(__file__).parent.resolve()
C_ROUTINES_DIR = PACKAGE_ROOT / 'src/c_routines'


class InstallWithExternalLibs(install):
    def run(self):
        proc = subprocess.run(f"cd {C_ROUTINES_DIR} && make install", shell=True)
        if proc.returncode != 0:
            exit(0)
        install.run(self)


class CleanWithExternalLibs(clean):
    def run(self):
        subprocess.run(f"cd {C_ROUTINES_DIR} && make clean", shell=True)
        clean.run(self)


with open('requirements.txt', 'r') as f:
    requirements = []
    for line in f:
        requirements.append(line)

setup(
    name='tasdmc',
    version='0.0.1',
    author='Igor Vaiman',
    description='Telescope Array Surface Detectors Monte Carlo pipeline',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=requirements,
    entry_points={
        'console_scripts': ['tasdmc=tasdmc.cli:cli'],
    },
    cmdclass={
        'install': InstallWithExternalLibs,
        'clean': CleanWithExternalLibs,
    },
)
