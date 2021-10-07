from setuptools import setup, find_packages, Extension
from setuptools.command.install import install
from distutils.command.clean import clean

import subprocess
import os
from pathlib import Path


package_root = Path(__file__).parent.resolve()
extensions_source_dir = package_root / 'src/extensions'
tasdmc_lib_dir = os.environ.get('TASDMC_LIB_DIR')
if tasdmc_lib_dir is None:
    raise EnvironmentError("TASDMC_LIB_DIR envirnoment variable must be set before installing the package!")
tasdmc_ext_module = Extension(
    "tasdmc.tasdmc_ext",
    sources=[str(package_root / 'src/tasdmc_ext.c')],
    library_dirs=[str(tasdmc_lib_dir)],
    libraries=['corsika_split_th'],
    extra_compile_args=[f'-I{extensions_source_dir}'],
)


class InstallWithExternalLibs(install):
    def run(self):
        subprocess.run(f"cd {extensions_source_dir} && make install", shell=True)
        install.run(self)


class CleanWithExternalLibs(clean):
    def run(self):
        subprocess.run(f"cd {extensions_source_dir} && make clean", shell=True)
        clean.run(self)


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
    ext_modules=[tasdmc_ext_module],
    install_requires=requirements,
    entry_points={
        'console_scripts': ['tasdmc=tasdmc.cli:cli'],
    },
    cmdclass={
        'install': InstallWithExternalLibs,
        'clean': CleanWithExternalLibs,
    },
)
