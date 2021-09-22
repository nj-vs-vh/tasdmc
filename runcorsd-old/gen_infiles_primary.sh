#!/bin/bash

# particle types supported and their CORSIKA ids
declare -A PARTID
PARTID["proton"]=14
PARTID["helium"]=402
PARTID["nitrogen"]=1407
PARTID["iron"]=5626

# string of accepted particle types
ACCEPTED_PARTID=
for k in "${!PARTID[@]}"; do
  ACCEPTED_PARTID="$ACCEPTED_PARTID $k"
done

corcard=$(dirname $(readlink -f $0))/corcard.py
test ! -x $corcard && echo "ERROR: $corcard executable not found!" >&2 && exit 2

emin=17.5
emax=20.5
step=0.1
if [ $# -gt 5 -o $# -lt 2 ]; then
    echo "(1): particle type: $ACCEPTED_PARTID" >&2
    echo "(2): output directory for card files" >&2
    echo "(3): (opt) minimum energy, default is ${emin}" >&2
    echo "(4): (opt) maximum energy, default is ${emax}" >&2
    echo "(5): (opt) use EPOS hadronic model? If so, type 'EPOS' for argument 5" >&2
    echo "Input files are generated for energies from minimum to maximum ( log10(E/eV) )" >&2
    echo "using 0.1 step. All log10(E/eV) must be rounded to 1 decimal point." >&2
    echo "Numbers of events are same as those used by B. T. Stokes at each energy." >&2
    echo "Zenith angles are allowed to be randomly chosen" >&2
    echo "by CORSIKA in range [0:60 degrees] from sin(theta)*cos(theta)." >&2
    exit 1
fi
part_type=$(echo $1 | tr '[:upper:]' '[:lower:]')
if [ ! ${PARTID[$part_type]+isset} ]; then
  echo "ERROR: invalid particle type: $1" >&2
  echo "ERROR: cardfile particle type must be one of: $ACCEPTED_PARTID"
  exit 2
fi
out_dir=${2%/}
test ! -d $out_dir && echo "ERROR: directory '${out_dir}' not found!" >&2 && exit 2
out_dir=$(readlink -f $out_dir)

re_num='^[0-9]+([.][0-9]+)?$'
if [ $# -ge 3 ]; then
    if ! [[ $3 =~ $re_num ]] ; then
	echo "ERROR: argument 3 ('${3}') is not a number" >&2 
	exit 2
    fi
    emin=$3
fi
if [ $# -ge 4 ]; then
    if ! [[ $4 =~ $re_num ]] ; then
	echo "ERROR: argument 4 ('${4}') is not a number" >&2 
	exit 2
    fi
    emax=$4
fi
EPOS=""
if [ $# -ge 5 ]; then
    YOUR_EPOS=$(echo $5 | tr '[:lower:]' '[:upper:]')
    if ! [[ $YOUR_EPOS == "EPOS" ]] ; then
	echo "ERROR: use word 'EPOS' for argument 5 (not '${YOUR_EPOS}') to generate cards for EPOS model" >&2
	exit 2
    fi
    EPOS="-${YOUR_EPOS}"
fi


nstp=$(echo ${emin} ${emax} ${step} | awk '{print int(($2-$1)/$3+1)}')
for i in $(seq 0 1 $((nstp-1))); do
    e=$(echo $emin $step $i | awk '{printf("%.1f",$1+$2*($3/1.0));}')
    $corcard -BTS ${EPOS} -e $e -p ${PARTID[$part_type]} -o $out_dir
done
exit 0
