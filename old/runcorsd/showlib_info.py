#!/usr/bin/env python

import argparse
import os
import sys
import subprocess
import re
from array import array
import struct
import math
from signal import signal, SIGPIPE, SIG_DFL


pattern_energy_id=re.compile(r"""
.*DAT\d\d\d\d(?P<energy_id>\d\d).*
""",re.VERBOSE)


def exe_shell_cmd(cmd):
    p=subprocess.Popen(cmd,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       shell = True,
                       preexec_fn = lambda: signal(SIGPIPE, SIG_DFL))
    return p.communicate()

def get_gea_dat_bytes_from_tar_gz_file(fname,nbytes):
    if not os.path.isfile(fname):
        sys.stderr.write('warning: failed to get info from {0:s}, the file doesn\'t exist\n'
                         .format(fname))
        return None
    if not fname.endswith('.tar.gz'):
        sys.stderr.write('warning: failed to get info from {0:s}, the file doesn\'t end with \'.tar.gz\'\n'
                         .format(fname))
        return None
    gea_dat=os.path.basename(fname)[0:9]+"_gea.dat"
    cmd='tar -O -xzf {0:s} {1:s} | head -c {2:d}'.format(fname,gea_dat,nbytes)
    buf, err = exe_shell_cmd(cmd)
    if(len(err) > 0):
        sys.stderr.write("{0:s}\n".format(err))
        return None
    return buf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files',nargs='*',
                        help='pass shower library files DAT??????_gea.dat or DAT??????.*.tar.gz from the command line')
    
    
    args = parser.parse_args()
    
    if len(args.files) < 1:
        sys.stderr.write("\nPrint information about the shower tile file\n");
        parser.print_help()
        return
    
    flist_rel=args.files

    flist=map(lambda s: os.path.abspath(s), flist_rel)

    NWORD = int(273)


    for fname in flist:
        if(not os.path.isfile(fname)) :
            sys.stderr.write('Error: file \'%s\' not found;' % (fname))
            sys.stderr.write(' SKIPPING\n');
        match=pattern_energy_id.match(fname)
        energy_id=int(0)
        if(match != None):
            energy_id=int(match.group("energy_id"))
        else:
            continue
        eventbuf=None
        if (fname.endswith("_gea.dat")):
            with open(fname,"rb") as f:
                eventbuf=struct.unpack(NWORD*'f', f.read(NWORD*4))
        elif (fname.endswith(".tar.gz")):
            buf = get_gea_dat_bytes_from_tar_gz_file(fname,NWORD*4)
            if(buf != None):
                eventbuf=struct.unpack(NWORD*'f', buf)
        else:
            sys.stderr.write('Error: file \'%s\' doesn not end with known extensions _gea.dat or .tar.gz;' % (fname))
            sys.stderr.write(' SKIPPING\n');
            continue

        if eventbuf != None:
            line="energy_id={0:02d} ptype={1:02d} log10en={2:.2f} theta={3:.2f}".\
                format(energy_id,int(eventbuf[2]),9.0+math.log10(eventbuf[3]),\
                           180.0/math.pi*eventbuf[10])
            sys.stdout.write(line+"\n");

if __name__=="__main__":
    main()
