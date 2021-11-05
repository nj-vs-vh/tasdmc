# Building `conda` package for easy `tasdmc` installation

This directory contains `conda-build` recipe that is used to create portable archive with
package build that can be easily moved to another machine and installed in one command.

## Building

Make sure that conda is installed, `base` environment is activated and `conda-build` package is
installed:

```bash
conda activate base
conda install conda-build
```

Then enter recipe directory and run

```bash
cd conda-build-recipe
conda config --add channels conda-forge
conda build . > cb.log
```

The build takes about 10 minutes due to large build-time dependency on CERN ROOT (TODO: remove
it by separating ROOT-independent part of sdanalysis).

After the build is done the package tarball can be found in `$CONDA_PREFIX/conda-bld/linux-64/tasdmc-?.?.?-py39_0.tar.bz2`:

## Local installation

To install newly-build package, use (`local-tasdmc-test` is the name of the environment to install to)

```bash
conda create -n local-tasdmc-test -c local tasdmc
conda activate local-tasdmc-test
# usual post-installation configuration as described in README
```

## Uploading to Anaconda

Register at [anaconda website](https://anaconda.org) and install (in `base` environment) `anaconda-client` package.
Then use it to login to your account

```bash
conda activate base
conda install anaconda-client
anaconda login
anaconda upload $CONDA_PREFIX/conda-bld/linux-64/tasdmc-?.?.?-py39_0.tar.bz2
```

Now `tasdmc` installation is available with

```bash
conda install -c your-account-name tasdmc
```
