from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = []
    for line in f:
        requirements.append(line)

setup(
    name='tasdmc',
    version='0.0.1',
    author='Igor Vaiman',
    description="Telescope Array Surface Detectors Monte Carlo scripts",
    packages=find_packages(where='src'),
    package_dir={"": "src"},
    install_requires=requirements,
)
