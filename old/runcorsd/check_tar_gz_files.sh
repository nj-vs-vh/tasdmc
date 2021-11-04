#!/usr/bin/env bash

# program that checks DAT??????_gea.dat files
check_gea_dat_file=$(dirname $(readlink -f $0))/check_gea_dat_file.run
test ! -x $check_gea_dat_file && echo "error: executable ${check_gea_dat_file} not found" && exit 2

# this one is subject to change
MIN_CORSIKA_LONG_FILE_LENGTH=1500


check_tar_gz_file()
{
    t=$1
    b=$(basename $t | sed 's/\(DAT[0-9][0-9][0-9][0-9][0-9][0-9]\).*/\1/')
    corsika_err=./${b}.CORSIKA.err
    dat_file=$b'_gea.dat'
    corsika_long_file='./'$b'.long'
    if [ ! -f $t ]; then
	echo "$t FILE NOT FOUND"
	return
    fi
    corsika_stat=$(tar -O -xzf $t $corsika_err 2>&1 | grep -v 'Note: The following floating-point exceptions are signalling' | wc -l)
    if [ $corsika_stat -gt 0 ]; then
	echo "$t CORSIKA FAILED"
	return
    fi
    line=$(tar -tzvf $t $dat_file 2>/dev/null | head -1)
    n=$(echo $line | awk '{print NF}')
    if [ $n -lt 6 ]; then
	echo "$t CORRUPTED"
	return
    fi
    status=$(tar -O -xzf $t $dat_file 2>/dev/null | ${check_gea_dat_file} --stdin 2>/dev/null | grep 'OK')
    if [ ${#status} -lt 2 ]; then
	echo "$t CORRUPTED"
	return
    fi
    ebin=$(echo $b | sed 's/DAT....//' | awk '{print $1/1}')
    size=$(echo $line | awk '{print $3}')
    if [ $size -lt 1024 ]; then
	exp_size=${TYP_SIZE_B[$ebin]}
        fract_err=${TYP_SIZE_FRACT_ERR[$ebin]}
        echo "$t TOO SMALL: GOT ${size}"
        return
    fi
    corsika_long_file_length=$(tar -O -xzf $t $corsika_long_file 2>&1 | wc -l)
    if [ $corsika_long_file_length -lt $MIN_CORSIKA_LONG_FILE_LENGTH ]; then
	echo "$t CORSIKA LONG FILE LENGTH LESS THAN ${MIN_CORSIKA_LONG_FILE_LENGTH}"
	return
    fi
    echo "$t OK"
    return
}


if [ $# -lt 1 -o $# -gt 2 ]; then
    echo "(1): ASCII list file with full paths to DAT??????.corsika.*.tar.gz files" >&2
    echo "(2): Number of threads" >&2
    echo "ALTERNATIVELY:" >&2
    echo "(1): A single DAT??????.corsika.*.tar.gz file" >&2
    exit 0
fi

if [ $# -eq 1 ]; then
    check_tar_gz_file $1 &
    wait
    exit 0
fi

listfile=$1
test ! -f $listfile && echo "error: list file ${listfile} not found" >&2 && exit 2
listfile=$(readlink -f $listfile)
nthreads=$2

i=0
while read tar_gz_file_name
do
   ((i=i%nthreads)); ((i++==0)) && wait
    check_tar_gz_file ${tar_gz_file_name} &
done < $listfile

wait
exit 0
