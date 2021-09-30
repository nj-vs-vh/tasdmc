#!/bin/bash

export RUNCORSD_BINDIR=/storage/vol2/zhezher/corsika-77100/run
export DSTDIR=/storage/vol2/zhezher/sdmc/prog/sdanalysis_2019_alpha/dst2k-ta
export COMMON_RESOURCE_DIRECTORY_LOCAL=/storage/vol2/zhezher/corsika-77100/run
source corsika_env.sh

#ls /storage/vol2/zhezher/sdmc_ur/infiles_p_qii/*in > filelist.txt

cat filelist.txt | sort -R | split -l 281 - list_part

for f in list_part*;
do
(cat $f | while read line; do 
	echo $line;
	./run_cor_dc2s_gea.sh $line /storage/vol2/zhezher/sdmc_ur/pro/ /storage/vol2/zhezher/sdmc_ur/gmd_p_qii4_urqmd/;
    done;) &
done

rm list_part*
rm filelist.txt
