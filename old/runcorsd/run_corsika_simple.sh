# testing

# dummy values
export RUNCORSD_BINDIR=/home/njvh/Documents/Science/ta/tasdmc/runcorsd-old/dummy_dir
export DSTDIR=/home/njvh/Documents/Science/ta/tasdmc/runcorsd-old/dummy_dir
export COMMON_RESOURCE_DIRECTORY_LOCAL=/home/njvh/Documents/Science/ta/tasdmc/runcorsd-old/dummy_dir
source corsika_env.sh

input_file=/home/njvh/Documents/Science/ta/tasdmc/runs/test-run/infiles/DAT004026.in
pro_dir=$COMMON_RESOURCE_DIRECTORY_LOCAL/pro
res_dir=$COMMON_RESOURCE_DIRECTORY_LOCAL/res

./run_cor_dc2s_gea.sh $input_file $pro_dir $res_dir
