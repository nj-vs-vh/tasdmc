ulimit -s unlimited

#                                                 n events | seed
sdmc_spctr_2g_gcc_x86.run ./tile_tampered.dat spctr_2.dst.gz 100 1312 1 ../data/sdcalib_test/sdcalib_001.bin ../data/atmos.bin
