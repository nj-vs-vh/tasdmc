#!/usr/bin/env bash

MYNAME=$(basename $0)

# Minimum number of lines one should expect in the CORSIKA .long file
MIN_CORSIKA_LONG_FILE_LENGTH=1500

# in case if something doesn't work then save the information that describes why it didn't work
fail=0
cmdargs_given=1  # true | false
# temp_log='/tmp/'${MYNAME}'_'${USER}_${RANDOM}_'temp.log'
temp_log=temp.log
touch $temp_log
echo "START: "${HOSTNAME}" "$(date +"%Y%m%d %H%M%S %Z") >>$temp_log

# Default CORSIKA executable file
# NOTE: FLUKA sources need to be available and the FLUKA top level directory
# must be pointed to by FLUPRO environment variable
if [ ${#FLUPRO} -eq 0 ]; then
    fail=$((fail + 1))
    echo "error(${fail}): FLUPRO variable (/full/paht/to/fluka/top/level/directory) not set!" >>$temp_log
else
    test ! -d $FLUPRO && fail=$((fail + 1)) && echo "error(${fail}): can't find ${FLUPRO} directory of FLUKA sources" >>$temp_log
fi
if [ ${#corexe} -eq 0 ]; then
    corexe=corsika73695Linux_QGSII_fluka
fi
# Default CORSIKA version
if [ ${#corver} -eq 0 ]; then
    corver=corsika73695
fi
# Default Hadronic model
if [ ${#hadrmod} -eq 0 ]; then
    hadrmod=qgsjetII.3
fi
# Default dethinning blur factor
if [ ${#BLURFACTOR} -eq 0 ]; then
    BLURFACTOR=5
fi
# Default dethinning binary file
if [ ${#dwtexe} -eq 0 ]; then
    dwtexe=deweight
fi
# geant/tile file creator
# see the note below about the _Xg part of the file name.
if [ ${#c2g_node_memory} -eq 0 ]; then
    c2g_node_memory=2
fi
if [ ${#c2g_sdgeant} -eq 0 ]; then
    c2g_sdgeant=sdgeant.dst
fi
if [ ${#c2gexe} -eq 0 ]; then
    c2gexe=corsika2geant_${c2g_node_memory}g
fi
if [ ${#check_gea_dat_file} -eq 0 ]; then
    check_gea_dat_file=check_gea_dat_file
fi
if [ ${#THREADS_PER_NODE} -eq 0 ]; then
    THREADS_PER_NODE=6
fi

# how to run the deweighting step. if you run in parallel, then these
# scripts should be run on a node at one time. if you run serial, then you
# can run multiple copies of this script at the same time. you still
# need to tailor your jobs for memory usage and disk usage though...
# If there OPTPARALLEL environmental variable is not set then set it to
# the default zero (meaning not parallel, serial mode)
if [ ${#OPTPARALLEL} -eq 0 ]; then
    OPTPARALLEL=0
fi

# file that records useful information about this run
LOGFILE=

# this contains all of binary and DATA files that are needed to run CORSIKA
if [ ${#COMMON_RESOURCE_DIRECTORY_LOCAL} -eq 0 ]; then
    fail=$((fail + 1))
    echo "error(${fail}): COMMON_RESOURCE_DIRECTORY_LOCAL not set!" >>$temp_log
else
    test ! -d ${COMMON_RESOURCE_DIRECTORY_LOCAL} &&
        fail=$((fail + 1)) &&
        echo "error(${fail}): " \
            "COMMON_RESOURCE_DIRECTORY_LOCAL='${COMMON_RESOURCE_DIRECTORY_LOCAL}' directory not found!" >>$temp_log
fi

if [ $# -ne 3 ]; then
    echo "runs CORSIKA on an input card file" >>$temp_log
    echo "(1): input card file" >>$temp_log
    echo "(2): processing directory" >>$temp_log
    echo "(3): output directory" >>$temp_log
    cmdargs_given=0
fi

infile=""
prodir=""
outdir=""

if [ $cmdargs_given -eq 1 ]; then
    infile=$1
    if [ ! -f $infile ]; then
        fail=$((fail + 1))
        echo "error(${fail}): input file infile '$infile' doesn't exist" >>$temp_log
    else
        infile=$(readlink -f $infile)
    fi
    prodir=$2
    if [ ! -d $prodir ]; then
        fail=$((fail + 1))
        echo "error(${fail}): processing directory '$prodir' doesn't exist" >>$temp_log
        prodir=""
    else
        prodir=$(readlink -f $2)
    fi
    outdir=$3
    if [ ! -d $outdir ]; then
        fail=$((fail + 1))
        echo "error(${fail}): output directory '$outdir' doesn't exist" >>$temp_log
        outdir=""
    else
        outdir=$(readlink -f $3)
    fi
fi

# basename of the input file
test -z $infile && infile=$(basename $0)'_'${USER}_${RANDOM}_'something_failed.in'
fbase=$(basename $infile)
# strip off the known dst suffixes
fbase0=$(basename $infile .in)

# make a local directory within which we're running CORSIKA
rnd_suf='_'$(date +%s)'_'$RANDOM
test -z $prodir && prodir="/tmp"
prodir_local=$prodir/$fbase0$rnd_suf
mkdir -p $prodir_local
test ! -d $prodir_local && fail=$((fail + 1)) && echo "error(${fail}): failed to create $prodir_local directory" >>$temp_log

# clean up procedure in case the script gets one of the termination signals
cleanup() {
    rm -rf $prodir_local
    echo "${MYNAME}: CLEAN UP ${prodir_local}" >&2
    echo "${MYNAME}: CLEAN UP ${prodir_local}"
    trap - SIGCONT SIGINT SIGKILL SIGTERM SIGSTOP # clear the trap
    PGID=$(ps -o pgid= $$ | grep -o [0-9]*)
    setsid kill -- -$PGID
    exit 2 # exit
}
trap cleanup SIGCONT SIGINT SIGKILL SIGTERM SIGSTOP

final_check_of_tar_gz_file() {
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
    status=$(tar -O -xzf $t $dat_file 2>/dev/null | ./${check_gea_dat_file} --stdin 2>/dev/null | grep 'OK')
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

# main running loop
while [ $fail -eq 0 -a $cmdargs_given -eq 1 ]; do

    # Copy all CORSIKA binaries and input card file to the local processing directory
    # and check and make sure that the CORSIKA executable and the input file are there
    rsync -au $COMMON_RESOURCE_DIRECTORY_LOCAL/* $prodir_local/.
    rsync -au $infile $prodir_local/.
    test ! -e $prodir_local/$corexe && fail=$((fail + 1)) &&
        echo "error(${fail}): failed to copy $corexe as executable to $prodir_local" >>$temp_log
    test ! -f $prodir_local/$fbase && fail=$((fail + 1)) &&
        echo "error(${fail}): failed to copy $infile to $prodir_local" >>$temp_log
    test ! -e $prodir_local/$dwtexe && fail=$((fail + 1)) &&
        echo "error(${fail}): failed to copy $dwtexe as executable to $prodir_local" >>$temp_log
    test ! -e $prodir_local/$c2gexe && fail=$((fail + 1)) &&
        echo "error(${fail}): failed to copy $c2gexe as executable to $prodir_local" >>$temp_log
    test ! -e $prodir_local/$c2g_sdgeant && fail=$((fail + 1)) &&
        echo "error(${fail}): failed to copy $c2g_sdgeant to $prodir_local" >>$temp_log
    test ! -e $prodir_local/$check_gea_dat_file && fail=$((fail + 1)) &&
        echo "error(${fail}): failed to copy $check_gea_dat_file to $prodir_local" >>$temp_log

    # If things did not get copied properly then break out of the main loop
    test $fail -gt 0 && break

    # save whatever the current directory is
    # and go to the local processing directory
    cur_dir=$(readlink -f $(pwd))
    cd $prodir_local

    # Set up all input/output file names in the local
    # processing directory
    crdfile=./$fbase                                 # Input card file
    outfile=./$fbase0.CORSIKA.out                    # Standard output file
    errfile=./$fbase0.CORSIKA.err                    # Standard error file
    longfile=./$fbase0.long                          # Longitudinal profile file
    partfile=./$fbase0                               # Particle file
    targzout=$prodir/$fbase0.$corver.$hadrmod.tar.gz # All of INPUT/OUTPUT information

    # Produce the logfile
    LOGFILE=$fbase0.settings.txt
    test -f $LOGFILE && rm $LOGFILE
    echo $(date) >>$LOGFILE
    echo USER: $USER >>$LOGFILE
    echo HOSTNAME: $HOSTNAME >>$LOGFILE
    echo CORSIKA EXE: $corexe >>$LOGFILE
    echo CORSIKA VER: $corver >>$LOGFILE
    echo HADRONIC MODEL: $hadrmod >>$LOGFILE
    echo DEWEIGHT BLURFACTOR: $BLURFACTOR >>$LOGFILE
    echo CORSIKA2GEANT: $c2gexe >>$LOGFILE
    echo THREADS_PER_NODE: $THREADS_PER_NODE >>$LOGFILE
    echo LOCAL_SRATCH_SPACE: $prodir_local >>$LOGFILE

    # run CORSIKA
    echo "Run CORSIKA and corsika_split-th" >>$LOGFILE
    space_needed_Gb=0.5
    available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
    have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    while [ $have_space -eq 0 ]; do
        echo "$(date +"%Y%m%d %H%M%S %Z"): INSUFFICIENT STORAGE ON ${HOSTNAME}:${prodir_local}  - WAIT 10 MINUTES" >>$LOGFILE
        sleep 10m
        available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
        have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    done
    # RUN CORSIKA and split the output file into parts
    (time ./$corexe <$crdfile 1>$outfile 2>$errfile) 2>>$LOGFILE
    # Stop if CORSIKA has failed in any (known) ways

    # checking corsika exit code
    if [ $? -ne 0 ]; then
        fail=$((fail + 1))
        echo "error(${fail}): CORSIKA EXECUTION FAILED" >>$temp_log
        cat $errfile >>$temp_log
        rm -rf $prodir_local
        break
    fi

    # counting lines in stderr excluding ones starting with "Note: The following floating-point exceptions are signalling"
    corsika_stat=$(cat $errfile 2>&1 | grep -v 'Note: The following floating-point exceptions are signalling' | wc -l)
    if [ $corsika_stat -gt 0 ]; then
        fail=$((fail + 1))
        echo "error(${fail}): CORSIKA FAILED: STDERR FILE DOESN'T EXIST OR CONTAINS ERRORS" >>$temp_log
        cat $errfile >>$temp_log
        rm -rf $prodir_local
        break
    fi

    # counting lines in corsika long file
    corsika_long_file_length=$(cat $longfile 2>&1 | wc -l)
    if [ $corsika_long_file_length -lt $MIN_CORSIKA_LONG_FILE_LENGTH ]; then
        fail=$((fail + 1))
        echo "error(${fail}): CORSIKA LONG FILE LENGTH LESS THAN ${MIN_CORSIKA_LONG_FILE_LENGTH}" >>$temp_log
        cat $errfile >>$temp_log
        break
    fi

    (time ./corsika_split-th $fbase0 $THREADS_PER_NODE) 2>>$LOGFILE
    echo "Finish Run CORSIKA and corsika_split-th" >>$LOGFILE
    SPLIT_FILES=""
    for ((N = 1; N <= $THREADS_PER_NODE; N++)); do
        F=$(printf "%s.p%02d" $fbase0 $N)
        if [ ! -f $F ]; then
            fail=$((fail + 1))
            echo "error(${fail}): can't read $F" >>$temp_log
        fi
        SPLIT_FILES+="$F "
    done
    if [ ${#SPLIT_FILES} -eq 0 ]; then
        fail=$((fail + 1))
        echo "error(${fail}): no DAT split files" >>$temp_log
        cat $errfile >>$temp_log
        rm -rf $prodir_local
        break
    fi

    # Now run dethinning. Ben's build scripts expect two parameters in the
    # build process:
    # 1. memory per node (in GB)
    # 2. memory per thread (in GB)
    # these parameters change the binaries (changing array capacities)
    # and change the name of the binary.
    # this script is not going to be so clever in dynamically selecting
    # difference memory limits and thread/node limits. so I am
    # building with:
    # bld 2
    # therefore the binaries will have a name with _2 attached to them.
    # if you rebuild the binaries then you may have to make a different
    # choice.
    #
    # Ben calls corsika_split-th here for the case in which you may
    # run multiple jobs per script invocation. we will not do that here.
    dwt_outfile=$fbase0.DEWEIGHT.out
    dwt_errfile=$fbase0.DEWEIGHT.err
    # the expected output file should be named something like
    # DATXXXXYY_dwt_F
    # where F is the BLURFACTOR defined in deweight.h. I'm continuing to
    # use BLURFACTOR = 5 as Ben has last set it.
    #dwtfile=${fbase0}_dwt_${BLURFACTOR}

    if [ $OPTPARALLEL -eq 1 ]; then
        echo "Run DETHIN in PARALLEL mode " $(date +"%Y%m%d %H%M%S %Z") >>$LOGFILE
    else
        echo "Run DETHIN in SERIAL mode " $(date +"%Y%m%d %H%M%S %Z") >>$LOGFILE
    fi

    # make sure we have enough disk space before proceeding with dethinning
    space_needed_Gb=100.0
    available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
    have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    while [ $have_space -eq 0 ]; do
        echo "$(date +"%Y%m%d %H%M%S %Z"): INSUFFICIENT STORAGE ON ${HOSTNAME}:${prodir_local}  - WAIT 10 MINUTES" >>$LOGFILE
        sleep 10m
        available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
        have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    done

    for F in $SPLIT_FILES; do
        if [ $OPTPARALLEL -eq 1 ]; then
            ./$dwtexe $F 1>$dwt_outfile 2>$dwt_errfile &
        else
            (time ./$dwtexe $F 1>$dwt_outfile 2>$dwt_errfile) 2>>$LOGFILE
        fi
    done
    wait

    if [ $OPTPARALLEL -eq 1 ]; then
        echo "Finish Run DETHIN in PARALLEL mode " $(date +"%Y%m%d %H%M%S %Z") >>$LOGFILE
    else
        echo "Finish Run DETHIN in SERIAL mode " $(date +"%Y%m%d %H%M%S %Z") >>$LOGFILE
    fi

    # create the "tile file"
    c2g_outfile=$fbase0.C2G.out
    c2g_errfile=$fbase0.C2G.err
    c2gfile=${fbase0}_gea.dat
    c2g_filelist=${fbase0}_c2g

    ls *dwt* >$c2g_filelist
    echo "Run CORSIKA2GEANT" >>$LOGFILE
    space_needed_Gb=0.5
    available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
    have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    while [ $have_space -eq 0 ]; do
        echo "$(date +"%Y%m%d %H%M%S %Z"): INSUFFICIENT STORAGE ON ${HOSTNAME}:${prodir_local}  - WAIT 10 MINUTES" >>$LOGFILE
        sleep 10m
        available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
        have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    done
    (time ./$c2gexe $c2g_filelist $c2g_sdgeant 1>$c2g_outfile 2>$c2g_errfile) 2>>$LOGFILE
    if [ $? -ne 0 ]; then
        fail=$((fail + 1))
        echo "error(${fail}): CORSIKA-TO-GEANT EXECUTION FAILED" >>$temp_log
        cat $c2g_errfile >>$temp_log
        cat $LOGFILE >>$temp_log
        break
    fi
    mv ${c2g_filelist}_gea.dat $c2gfile 2>>$LOGFILE
    echo "Finish Run CORSIKA2GEANT" >>$LOGFILE
    status=$(./${check_gea_dat_file} -bin_f ${c2gfile} 2>>$LOGFILE | grep 'OK')
    if [ ${#status} -lt 2 ]; then
        fail=$((fail + 1))
        echo "error(${fail}): FAILED TILE FILE CHECK of ${c2gfile}" >>$temp_log
        cat $c2g_errfile >>$temp_log
        cat $LOGFILE >>$temp_log
        break
    fi

    # Combine all of CORSIKA INPUT/OUTPUT into a tar.gz file and move
    # the file to the designated output directory.
    # NOTE: $dwtfile is enormous and not retained. $partfile is not
    # saved either. the primary file of interest for this process is
    # $c2gfile (the "tile file").

    # clean up some space before making a tar-ball with the outputs
    scratchspace_used_h=$(du -csh $prodir_local 2>/dev/null | tail -1 | awk '{print $1}')
    echo USED_SRATCH_SPACE: $scratchspace_used_h >>$LOGFILE
    for f in $(cat $c2g_filelist); do
        rm -rf $f
    done
    rm -rf $fbase0
    rm -rf $SPLIT_FILES
    rm -rf tmp???

    echo "Pack and Send the Outputs" >>$LOGFILE
    space_needed_Gb=0.2
    available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
    have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    while [ $have_space -eq 0 ]; do
        echo "$(date +"%Y%m%d %H%M%S %Z"): INSUFFICIENT STORAGE ON ${HOSTNAME}:${prodir_local}  - WAIT 10 MINUTES" >>$LOGFILE
        sleep 10m
        available_disk_space_Gb=$(df . | grep -v Filesystem | head -1 | awk '{print $4/1048576.0}')
        have_space=$(echo $space_needed_Gb $available_disk_space_Gb | awk '{print int($2/$1)}')
    done

    tar -czf $targzout $longfile $crdfile $outfile $errfile \
        $dwt_outfile $dwt_errfile $c2gfile $c2g_outfile $c2g_errfile $LOGFILE 2>>$temp_log 2>>$LOGFILE
    status=$(final_check_of_tar_gz_file ${targzout} 2>&1)
    status_ok=$(echo "${status}" | grep "OK" | wc -l)
    if [ ${status_ok} -eq 0 ]; then
        fail=$((fail + 1))
        echo "error(${fail}): FAILED FINAL CHECK OF TAR-GZ FILE "$(basename ${targzout}) >>$temp_log
        echo "${status}" >>$temp_log
        break
    fi

    mv $targzout $outdir/. 2>>$temp_log
    echo "mv ${targzout} ${outdir}" >>$temp_log

    # clean up the local processing directory
    cd $cur_dir
    rm -rf $prodir_local

    # break out of the main loop after finished running successfully
    break
done

# if something failed, indicate the fail count
if [ $cmdargs_given -eq 0 ]; then
    echo "Command line arguments not given properly" >>$temp_log
    test $fail -gt 0 && echo "Besides the command line arguments, something else has failed, fail count = ${fail}" >>$temp_log
else
    test $fail -gt 0 && echo "Something has failed, fail count = ${fail}" >>$temp_log
fi
# if the output directory exists, then produce .done or .failed files, depending on the status
# of the execution. Otherwise, print everything into sdtderr.
echo "FINISH: "${HOSTNAME}" "$(date +"%Y%m%d %H%M%S %Z") >>$temp_log
if [ ! -z $outdir ]; then
    done_file=$outdir/$fbase'.done'
    failed_file=$outdir/$fbase'.failed'
    status_file=${done_file}
    test $fail -gt 0 && status_file=${failed_file}
    if [ $fail -gt 0 ]; then
        echo "fail count = ${fail}" >>${status_file}
    fi
    cat $temp_log >>${status_file}
else
    cat $temp_log >&2
fi
# rm -f $temp_log

# make sure the local processing directory is clean
test $fail -gt 0 && rm -rf $prodir_local

# Exit with the flag.  If success, then fail should be zero.
exit $fail
