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

if [ ! -d $dir/p1 ]; then
    mkdir $dir/p1
    totallines=`ls $dir/p0/*.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p0/*.dst.gz | sort -R | split -l $l - $dir/tmp/dstlist0_part

    for f in $dir/tmp/dstlist0_part*
    do
	rufptn.run -f -i $f -o $dir/p1/ >/dev/null 2>/dev/null &
    done
    wait

fi

if [ ! -d $dir/p2 ]; then
    mkdir $dir/p2
    totallines=`ls $dir/p1/*.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p1/*.dst.gz | sort -R | split -l $l - $dir/tmp/dstlist1_part

    for f in $dir/tmp/dstlist1_part*
    do
	rufldf.run -f -i $f -o $dir/p2/ >/dev/null 2>/dev/null &
    done
    wait
fi

sddbfile=$dir/$dir.sddb
errfile=$dir/$dir.err
if [ ! -f $sddbfile ]; then
    totallines=`ls $dir/p2/*.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p2/*.dst.gz | sort -R | split -l $l - $dir/tmp/dstlist2_part

    for f in $dir/tmp/dstlist2_part*
    do
	/storage/vol4/zhezher/sdmc/sdanalysis/nuf.i12aop/bin/nuf -geom $f 2>$f.err | grep SDDB > $f.sddb &
#	nuf.i12c.run $f 2>$f.err | grep SDDB > $f.sddb &
    done
    wait
    cat $dir/tmp/dstlist2_part*.sddb > $sddbfile
    cat $dir/tmp/dstlist2_part*.err > $errfile
fi

outfile=$dir/${dir}_ivanov.awk
errfile=$dir/${dir}_ivanov.err
if [ ! -f $outfile ]; then
    totallines=`ls $dir/p2/*.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p2/*.dst.gz | sort -R | split -l $l - $dir/tmp/dstlist3_part

    for f in $dir/tmp/dstlist3_part*
    do
	sdascii.run -no_bw -form 1 -i $f 2>${f}_ivanov.err > ${f}_ivanov.txt &
    done
    wait
    cat $dir/tmp/dstlist3_part*_ivanov.txt | grep EVT | sed s/"EVT  "// | sed s/,/\ /g | awk '{print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10}' > $outfile
    cat $dir/tmp/dstlist3_part*_ivanov.err > $errfile
fi

mcfile=$dir/$dir.MC
errfile=$dir/$dir.MC.err

if [ ! -f $mcfile ]; then
    totallines=`ls $dir/p0/*.dst.gz | wc -l`
    l=$((totallines/N+1))

    ls $dir/p0/*.dst.gz | sort -R | split -l $l - $dir/tmp/dstlist4_part

    for f in $dir/tmp/dstlist4_part*
    do
	sditerator_mc.run -i $f -o $f.MC >/dev/null 2>$f.MC.err &
    done
    wait
    cat $dir/tmp/dstlist4_part*.MC > $mcfile
    cat $dir/tmp/dstlist4_part*.MC.err > $errfile
fi

rm -f $dir/tmp/dstlist*
rmdir $dir/tmp
