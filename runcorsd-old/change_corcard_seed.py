#!/usr/bin/env python

import re
import math
import os
import sys
import numpy
import select
import argparse


# CORSIKA version 73695 allows random integer seeds in 1,900000000 range
# inclusively.  Getting an ntuple of 5 random seeds.
def get_5_cor_seeds():
    return numpy.random.random_integers(1,900000000,5)


class corcard:
    def __init__(self,infile):
        with open(infile,"r") as f:
            self.buf=f.read().strip()
    def replace_card(self,card_name,card_value,occurrence=1):
        class Nth(object):
            def __init__(self, n_min, n_max, replacement):
                if n_max < n_min:
                    n_min, n_max = n_max, n_min
                self.n_min = n_min
                self.n_max = n_max
                self.replacement = replacement
                self.calls = 0
            def __call__(self, matchobj):
                self.calls += 1
                if self.n_min <= self.calls <= self.n_max:
                    return self.replacement
                return matchobj.group(0)
        name=str(card_name)
        value=str(card_value)
        crd_original=r'{:s} .+'.format(name)
        crd_replaced=r'{:s} {:s}'.format(name,value)
        self.buf=re.sub(crd_original,Nth(occurrence,occurrence,crd_replaced),self.buf)
        
    def set_SEED(self,seed1,seed2,seed3,seed4,seed5):
        self.replace_card("SEED","{:d} 0 0".format(seed1),occurrence=1)
        self.replace_card("SEED","{:d} 0 0".format(seed2),occurrence=2)
        self.replace_card("SEED","{:d} 0 0".format(seed3),occurrence=3)
        self.replace_card("SEED","{:d} 0 0".format(seed4),occurrence=4)
        self.replace_card("SEED","{:d} 0 0".format(seed5),occurrence=5)
        

def main():

    parser = argparse.ArgumentParser()
    

    parser.add_argument('files',nargs='*',
                        help='pass .in file names w/o prefixes or switches or pipe them through stdin')
    parser.add_argument('-i', action='store', dest='listfile',
                        help='give an ascii list file with paths to a bunch of .in files')
    parser.add_argument('-o', action='store', dest='outdir', default=".", \
                            help='Output directory, default .')
    parser.add_argument('-f', action='store_true', default=False, dest='f_overwrite', \
                            help='Overwrite output files')
    have_stdin = False
    if select.select([sys.stdin,],[],[],0.0)[0]:
        have_stdin=True

    if (len(sys.argv)==1 and have_stdin==False):
        sys.stdout.write("\n");
        sys.stdout.write("Change the random seeds for the CORSIKA input files without altering any other parameters\n\n");
        parser.print_help()
        sys.stdout.write("\n\n")
        sys.exit(1)
    
    
    args = parser.parse_args()

 
    outdir=args.outdir
    if not os.path.isdir(outdir):
        sys.stderr.write("Error: {:s} directory not found\n".format(outdir))
        sys.exit(2)
    outdir=os.path.abspath(outdir)

    # get absolute paths to all existing unique infiles
    if args.files != None:
        infiles_rel=args.files
    if have_stdin:
        infiles_rel.extend(map(lambda s: s.strip(), sys.stdin.readlines()))
    if args.listfile != None:
        with open(args.listfile,"r") as f:
            infiles_rel.extend(map(lambda s: s.strip(), f.readlines()))
    infiles=map(lambda s: os.path.abspath(s), infiles_rel)
    infiles_all = []
    infiles_all.extend(infiles)
    for infile in infiles_all:
        if(not os.path.isfile(infile)) :
            sys.stderr.write('Error: file \'%s\' not found;' % (infile))
            sys.stderr.write(' SKIPPING\n');
            infiles.remove(infile)
    infiles = sorted(set(infiles))

    # now write out CORSIKA card files, using different sets of seeds for each file
    for infile in infiles:
        outfile=outdir+"/"+os.path.basename(infile)
        if not args.f_overwrite:
            if os.path.isfile(outfile):
                sys.stderr.write("error: file {0:s} exists; use -f to overwrite output flies\n"\
                                     .format(outfile))
                exit(2)
        card = corcard(infile)
        seeds=get_5_cor_seeds()
        card.set_SEED(seeds[0],seeds[1],seeds[2],seeds[3],seeds[4])
        with open(outfile,"w") as f:
            f.write(card.buf+"\n")
    
if __name__ == "__main__":
    main()
