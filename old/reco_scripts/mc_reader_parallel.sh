#!/usr/bin/env bash

if [ $# -ne 2 ]; then
    echo "">&2
    echo "Usage: $(basename $0) MC_dir N_threads">&2
    echo "        .dst.gz files are expected in MC_dir/p0">&2
    echo "">&2
    exit 1
fi

dir=$1
N=$2

if [ ! -d $dir/p0 ]; then
    echo "Error!">&2
    echo "The directory $dir/p0 doesn't exist">&2
    exit 2
fi

rm -f $dir/tmp/dstlist*
mkdir -p $dir/tmp

mcfile=$dir/$dir.MC
errfile=$dir/$dir.MC.err

if [ ! -f $mcfile ]; then
    totallines=`ls $dir/p0/*.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p0/*.dst.gz | split -l $l - $dir/tmp/dstlist4_part

    for f in $dir/tmp/dstlist4_part*
    do
	sditerator_mc.run -i $f -o $f.MC >/dev/null 2>$f.MC.err &
    done
    wait
    cat $dir/tmp/dstlist4_part*.MC > $mcfile
    cat $dir/tmp/dstlist4_part*.MC.err > $errfile
fi

rm -f $dir/tmp/dstlist4*
rmdir $dir/tmp
