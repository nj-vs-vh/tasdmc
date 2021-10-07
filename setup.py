from setuptools import setup, find_packages, Extension

import subprocess
import os
from pathlib import Path


# TODO: MAKE THIS PART EXECUTE ONLY ON INSTALL AND RUN make clean ON UNINSTALL

CUR_DIR = Path(__file__).parent.resolve()
extensions_source_dir = CUR_DIR / 'src/extensions'
tasdmc_lib_dir = os.environ.get('TASDMC_LIB_DIR')
if tasdmc_lib_dir is None:
    raise EnvironmentError("TASDMC_LIB_DIR envirnoment variable must be set before installing the package!")
subprocess.run(f"cd {extensions_source_dir} && make install", shell=True)  # building libs
tasdmc_ext_module = Extension(
    "tasdmc.tasdmc_ext",
    sources=[str(CUR_DIR / 'src/tasdmc_ext.c')],
    library_dirs=[str(tasdmc_lib_dir)],
    libraries=['corsika_split_th'],
    extra_compile_args=[f'-I{extensions_source_dir}'],
)


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
)
