# `tasdmc`-related utils

1. `dstreader` - SWIG-generated Python wrapper around `dst2k-ta` library, allows reading
   `.dst` files from Python. Currently supports only `rusdmc` and `rusdraw` banks, but
   easily extendable. See [examples](/src/utils/dstreader/examples)
2. `tile_vis.py` - small script to visualize the contents of tile-file
