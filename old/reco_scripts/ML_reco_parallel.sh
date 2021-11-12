#!/usr/bin/env bash

if [ $# -ne 3 ]; then
    echo "">&2
    echo "Usage: $(basename $0) MC_dir out_dir N_threads">&2
    echo "        .dst.gz files are expected in MC_dir/p0">&2
    echo "">&2
    exit 1
fi

dir=$1
outdir=$2
N=$3

if [ ! -d $dir/p2 ]; then
    echo "Error!">&2
    echo "The directory $dir/p2 doesn't exist">&2
    exit 2
fi

rm -f $outdir/tmp/dstlist*
mkdir -p $outdir/tmp

MLfile=$outdir/$dir.ML
errfile=$outdir/$dir.ML.err
if [ ! -f $MLfile ]; then
    totallines=`ls $dir/p2/*.rufldf.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p2/*.rufldf.dst.gz | split -l $l - $outdir/tmp/dstlist2_part

    for f in $outdir/tmp/dstlist2_part*
    do
	nuf.i12e.run -ML $f 2>$f.err > $f.ML &
    done
    wait
    cat $outdir/tmp/dstlist2_part*.ML > $MLfile
    cat $outdir/tmp/dstlist2_part*.err > $errfile
fi

rm -f $outdir/tmp/dstlist*
rmdir $outdir/tmp
