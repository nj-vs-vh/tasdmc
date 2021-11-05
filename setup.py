from setuptools import setup, find_packages
from src.tasdmc import __version__


with open('requirements.txt', 'r') as f:
    requirements = []
    for line in f:
        requirements.append(line)

setup(
    name='tasdmc',
    version=__version__,
    author='Igor Vaiman',
    description='Telescope Array Surface Detectors Monte Carlo pipeline',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    # install_requires=requirements,  # no requirements enforced in build-time
    entry_points={
        'console_scripts': ['tasdmc=tasdmc.cli:cli'],
    },
)
