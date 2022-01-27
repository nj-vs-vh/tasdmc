import os
import sys
import subprocess
import shutil
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.install import install
from swig.generate_numpy_accessors import generate_accessors

BANK_NAMES = ['rusdraw', 'rusdmc']

sdanalysis_dir = os.environ.get("SDANALYSIS_DIR")
assert sdanalysis_dir is not None, "SDANALYSIS_DIR environment variable must be defined"

CUR_DIR = Path(__file__).parent
SRC_DIR = CUR_DIR / "src"
SWIG_DIR = CUR_DIR / "swig"
SWIG_INTERFACE_TEMPLATE = SWIG_DIR / "dstreader_core_template.i"
SWIG_INTERFACE_FILE = SWIG_DIR / "dstreader_core.i"
SWIG_GENERATED_WRAPPER = SWIG_DIR / "dstreader_core_wrap.c"
SWIG_GENERATED_PY_MODULE = SWIG_DIR / "dstreader_core.py"
DST2K_TA_INC_DIR = Path(sdanalysis_dir) / "dst2k-ta/inc"
dst2k_ta_include = f"-I{DST2K_TA_INC_DIR}"
DST2K_TA_LIB_DIR = Path(sdanalysis_dir) / "dst2k-ta/lib"


class InstallWithSwig(install):
    def run(self):
        shutil.copy(SWIG_INTERFACE_TEMPLATE, SWIG_INTERFACE_FILE)
        doc_file = SRC_DIR / "bank_docs.py"
        doc_file.write_text("generated_bank_docs = {\n")
        for bank_name in BANK_NAMES:
            dst_bank_header = DST2K_TA_INC_DIR / f"{bank_name}_dst.h"
            assert dst_bank_header.exists(), f"Header for bank {bank_name} not found at {dst_bank_header}"
            accesors_interface_file = SWIG_DIR / f"{bank_name}_numpy_accessors.i"
            generate_accessors(dst_bank_header, accesors_interface_file, doc_file)
            with open(SWIG_INTERFACE_FILE, "a") as f:
                f.write(
                    f'\n%include "{dst_bank_header.name}"\n'
                    + f'%include "{accesors_interface_file.name}"\n'
                )
        with open(doc_file, "a") as f:
            f.write("}\n")

        cmdargs = ["swig", "-python", dst2k_ta_include, f"-I{SWIG_DIR}", str(SWIG_INTERFACE_FILE)]
        print(" ".join(cmdargs))
        res = subprocess.run(cmdargs, capture_output=True)
        if res.returncode != 0:
            print(res.stdout.decode("utf-8"))
            print(res.stderr.decode("utf-8"))
            sys.exit(1)
        
        swig_generated_module_in_src = SRC_DIR / SWIG_GENERATED_PY_MODULE.name
        swig_generated_module_in_src.unlink(missing_ok=True)
        shutil.move(SWIG_GENERATED_PY_MODULE, swig_generated_module_in_src)
        install.run(self)


core_ext = Extension(
    "dstreader._dstreader_core",
    sources=[f'{SWIG_DIR}/dstreader_core_wrap.c'],  # generated by swig
    swig_opts=[dst2k_ta_include],
    library_dirs=[str(DST2K_TA_LIB_DIR)],
    libraries=['dst2k', 'm', 'c', 'z', 'bz2'],
    extra_compile_args=[dst2k_ta_include],
)

setup(
    name='dstreader',
    version="0.0.1",
    author='Igor Vaiman',
    author_email='gosha.vaiman@gmail.com',
    description='TA/HiRes DST file format reader, SWIG-generated wrapper around dst2k-ta library',
    packages=['dstreader'],
    package_dir={'dstreader': 'src'},
    ext_modules=[core_ext],
    cmdclass={
        'install': InstallWithSwig,
    },
)
