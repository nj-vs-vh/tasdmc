#!/usr/bin/env python

import re
import math
import os
import sys
import numpy
import argparse
import getpass

#  To generate CORSIKA showers using B. T. Stokes optimal thinning 
#  parameters for each energy in 0.1 log10e bin and run number convention
#  index of the dictionary: energy, log10(E/eV)
#  For each log10(E/eV) value:
#   [0]         = last 2 digits (XX) of the corsika DAT????XX.in input file
#   (run number in CORSIKA card file is a 6 digit number XXXXXX in 
#   DATXXXXXX.in file name, the last 2 digits in XXXXXX identify the energy 
#   channel and the first 4 digits are just a sequential number from 0 to 9999 
#   [1],[2],[3] = three values of the CORSIKA THIN card
#   [4],[5]     = two values of the CORSIKA THINH card
#   [6]         = how many particles BTS would normally throw at each energy
BTS_PAR = {}



BTS_PAR[15.0] = (70, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 10000 )
BTS_PAR[15.1] = (71, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 10000 )
BTS_PAR[15.2] = (72, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 6300  )
BTS_PAR[15.3] = (73, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 4000  )
BTS_PAR[15.4] = (74, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 2500  )
BTS_PAR[15.5] = (75, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 1700  )
BTS_PAR[15.6] = (76, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 1000  )
BTS_PAR[15.7] = (77, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 650   )
BTS_PAR[15.8] = (78, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 400   )
BTS_PAR[15.9] = (79, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 250   )
BTS_PAR[16.0] = (80, 1.0E-6, 1.000000e+1, 10.e2,   1.0,  1.0E2, 250   )
BTS_PAR[16.1] = (81, 1.0E-6, 1.258925e+1, 10.e2,   1.0,  1.0E2, 1000  )
BTS_PAR[16.2] = (82, 1.0E-6, 1.584893e+1, 20.e2,   1.0,  1.0E2, 1000  )
BTS_PAR[16.3] = (83, 1.0E-6, 1.995262e+1, 40.e2,   1.0,  1.0E2, 1000  )
BTS_PAR[16.4] = (84, 1.0E-6, 2.511886e+1, 60.e2,   1.0,  1.0E2, 1000  )
BTS_PAR[16.5] = (85, 1.0E-6, 3.162278e+1, 80.e2,   1.0,  1.0E2, 1000  )
BTS_PAR[16.6] = (26, 1.0E-6, 3.981071e+1, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[16.7] = (27, 1.0E-6, 5.011872e+1, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[16.8] = (28, 1.0E-6, 6.309573e+1, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[16.9] = (29, 1.0E-6, 7.943282e+1, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[17.0] = (30, 1.0E-6, 1.000000e+2, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[17.1] = (31, 1.0E-6, 1.258925e+2, 100.e2,  1.0,  1.0E2, 10000 )
BTS_PAR[17.2] = (32, 1.0E-6, 1.584893e+2, 100.e2,  1.0,  1.0E2, 6300  )
BTS_PAR[17.3] = (33, 1.0E-6, 1.995262e+2, 100.e2,  1.0,  1.0E2, 4000  )
BTS_PAR[17.4] = (34, 1.0E-6, 2.511886e+2, 100.e2,  1.0,  1.0E2, 2500  )
BTS_PAR[17.5] = (35, 1.0E-6, 3.162278e+2, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[17.6] = (36, 1.0E-6, 3.981071e+2, 100.e2,  1.0,  1.0E2, 1000  )
BTS_PAR[17.7] = (37, 1.0E-6, 5.011872e+2, 100.e2,  1.0,  1.0E2, 650   )
BTS_PAR[17.8] = (38, 1.0E-6, 6.309573e+2, 100.e2,  1.0,  1.0E2, 400   )
BTS_PAR[17.9] = (39, 1.0E-6, 7.943282e+2, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.0] = (0,  1.0E-6, 1.000000e+3, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.1] = (1,  1.0E-6, 1.258925e+3, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.2] = (2,  1.0E-6, 1.584893e+3, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.3] = (3,  1.0E-6, 1.995262e+3, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.4] = (4,  1.0E-6, 2.511886e+3, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.5] = (5,  1.0E-6, 3.162278e+3, 100.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.6] = (6,  1.0E-6, 3.981071e+3, 140.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.7] = (7,  1.0E-6, 5.011872e+3, 180.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.8] = (8,  1.0E-6, 6.309573e+3, 220.e2,  1.0,  1.0E2, 250   )
BTS_PAR[18.9] = (9,  1.0E-6, 7.943282e+3, 260.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.0] = (10, 1.0E-6, 1.000000e+4, 300.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.1] = (11, 1.0E-6, 1.258925e+4, 350.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.2] = (12, 1.0E-6, 1.584893e+4, 400.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.3] = (13, 1.0E-6, 1.995262e+4, 450.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.4] = (14, 1.0E-6, 2.511886e+4, 500.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.5] = (15, 1.0E-6, 3.162278e+4, 550.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.6] = (16, 1.0E-6, 3.981071e+4, 600.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.7] = (17, 1.0E-6, 5.011872e+4, 650.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.8] = (18, 1.0E-6, 6.309573e+4, 700.e2,  1.0,  1.0E2, 250   )
BTS_PAR[19.9] = (19, 1.0E-6, 7.943282e+4, 750.e2,  1.0,  1.0E2, 250   )
BTS_PAR[20.0] = (20, 1.0E-6, 1.000000e+5, 800.e2,  1.0,  1.0E2, 250   )
BTS_PAR[20.1] = (21, 1.0E-6, 1.258925e+5, 850.e2,  1.0,  1.0E2, 250   )
BTS_PAR[20.2] = (22, 1.0E-6, 1.584893e+5, 900.e2,  1.0,  1.0E2, 250   )
BTS_PAR[20.3] = (23, 1.0E-6, 1.995262e+5, 950.e2,  1.0,  1.0E2, 250   )
BTS_PAR[20.4] = (24, 1.0E-6, 2.511886e+5, 1000.e2, 1.0,  1.0E2, 250   )
BTS_PAR[20.5] = (25, 1.0E-6, 3.162278e+5, 1050.e2, 1.0,  1.0E2, 250   )

# For QGSJET
BTS_SAMPLE_CARD_FILE='''
RUNNR 023905
DIRECT " "
PRMPAR 14
EVTNR 1
NSHOW 1
ESLOPE -2.7
ERANGE 3.162278e+9 3.162278e+9
THETAP 0.000000e+00 6.000000e+01
PHIP 0.000000e+00 0.000000e+00
ELMFLG  F   T
RADNKG  200.E2
FIXHEI  0.  0
FIXCHI  0.
OBSLEV 1430.e2
MAGNET  21.59 46.80
ARRANG  0.0
HADFLG  0  0  0  0  0  2
ECUTS   0.05  0.05  0.00025  0.00025
MUADDI  F
MUMULT  T
MAXPRT  0
ECTMAP  1.E8
TSTART  F
LONGI   T  1.  T  T
STEPFC  1.
DEBUG   F  6  F  1000000
USER    u0033896
HOST  chpc
THIN 1.E-6 3.162278e+3 100.e2
THINH 1. 1.E2
SEED 186605632 0 0
SEED 188366839 0 0
SEED 190836137 0 0
SEED 192595577 0 0
SEED 194324493 0 0
ATMOD   17
'''

# Additional EPOS cards
EPOS_CARDS='''
EPOS T 0
EPOSIG T
EPOPAR input epos/epos.param        !initialization input file for epos
EPOPAR fname inics epos/epos.inics  !initialization input file for epos
EPOPAR fname iniev epos/epos.iniev  !initialization input file for epos
EPOPAR fname initl epos/epos.initl  !initialization input file for epos
EPOPAR fname inirj epos/epos.inirj  !initialization input file for epos
EPOPAR fname inihy epos/epos.ini1b  !initialization input file for epos
EPOPAR fname check none                !dummy output file for epos
EPOPAR fname histo none                !dummy output file for epos
EPOPAR fname data  none                !dummy output file for epos
EPOPAR fname copy  none                !dummy output file for epos
'''

# Constants for the CORSIKA primary particle IDs
PRMPAR_PROTON=int(14)
PRMPAR_HELIUM=int(402)
PRMPAR_NITROGEN=int(1407)
PRMPAR_IRON=int(5626)


# CORSIKA version 73695 allows random integer seeds in 1,900000000 range
# inclusively.  Getting an ntuple of 5 random seeds.
def get_5_cor_seeds():
    return numpy.random.random_integers(1,900000000,5)


class corcard:
    def __init__(self):
        self.buf=BTS_SAMPLE_CARD_FILE.strip()
        self.epos_cards_added=False
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

    def set_RUNNR(self,runnr):
        self.replace_card("RUNNR","{:06d}".format(runnr))

    def set_ATMOD(self,atmod):
        self.replace_card("ATMOD","{:d}".format(atmod))

    def set_PRMPAR(self,prmpar):
        self.replace_card("PRMPAR","{:d}".format(prmpar))

    def set_fixed_log10en(self,log10en_eV):
        E_GeV=1e-9*math.pow(10.0,float(log10en_eV))
        val="{:.6E} {:.6E}".format(E_GeV,E_GeV).replace("+0","+")
        self.replace_card("ERANGE","{:.6E} {:.6E}".format(E_GeV,E_GeV)\
                              .replace("+0","+"))
    def set_fixed_theta(self,theta_deg):
        self.replace_card("THETAP","{:.2f} {:.2f}".format(theta_deg,theta_deg))
    
    def set_fixed_phi(self,phi_deg):
        self.replace_card("PHIP","{:.2f} {:.2f}".format(phi_deg,phi_deg))

    def set_THIN(self,val1,val2,val3):
        val="{:.1E} {:.6E} {:.2E}".format(val1,val2,val3)
        val=val.replace("+0","+")
        val=val.replace("-0","-")
        self.replace_card("THIN",val)
        
    def set_THINH(self,val1,val2):
        val="{:.1f} {:.1E}".format(val1,val2)
        val=val.replace("+0","+")
        val=val.replace("-0","-")
        self.replace_card("THINH",val)
        
    def set_SEED(self,seed1,seed2,seed3,seed4,seed5):
        self.replace_card("SEED","{:d} 0 0".format(seed1),occurrence=1)
        self.replace_card("SEED","{:d} 0 0".format(seed2),occurrence=2)
        self.replace_card("SEED","{:d} 0 0".format(seed3),occurrence=3)
        self.replace_card("SEED","{:d} 0 0".format(seed4),occurrence=4)
        self.replace_card("SEED","{:d} 0 0".format(seed5),occurrence=5)

    def set_USER(self,user):
        self.replace_card("USER",user)
        
    def set_HOST(self,host):
        self.replace_card("HOST",host)
        
    def add_EPOS_CARDS(self):
        if not self.epos_cards_added:
            self.buf = self.buf + "\n" + EPOS_CARDS.strip()
            self.epos_cards_added=True
        

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', action='store', dest='iprim', default=14, \
                            help='Primary ID, default 14 (proton)')
    parser.add_argument('-e', action='store', dest='log10en', required=True, \
                            help='log10(E/eV)')
    parser.add_argument('-BTS', action='store_true', dest='BTS', default=False, \
                            help='Generate the same number of events at the fixed energy as B. T. Stokes with random'+
                        ' event zenith angles.  If this option is used, then \'-imin\', \'-imax\', \'-the\' options'+
                        ' cannot be used.  The script will check that they are not used and print an error'
                        ' if they are being used.')
    parser.add_argument('-EPOS',action='store_true',dest='EPOS',default=False, \
                            help='To use EPOS-LHC hadronic interraction model, false by default.')
    parser.add_argument('-imin', action='store', dest='imin', \
                            help='Minimum file index, default is 0')
    parser.add_argument('-imax', action='store', dest='imax', \
                            help='Maximum file index (different random seeds for different files), default is 0')
    parser.add_argument('-o', action='store', dest='outdir', default=".", \
                            help='Output directory, default .')
    parser.add_argument('-the', action='store', dest='theta', \
                            help='Zenith angle [ Degree ] to run at fixed zenith angle.'+
                        'By default, generates random zenith angles from sin(theta)*cos(theta) in'
                        ' 0 to 60 degree range.')
    parser.add_argument('-v', action='store', dest='verbosity',default=1,help='verbosity, default is 1')


    if (len(sys.argv)==1):
        sys.stdout.write("\n");
        sys.stdout.write("Generate CORSIKA input card files with B. T. Stokes thinning parameters\n\n");
        parser.print_help()
        sys.stdout.write("\n\n")
        sys.exit(1)
    
    card = corcard()
    
    # set user name to current user and set host name to chpc
    card.set_USER(getpass.getuser());
    card.set_HOST("chpc")
    
    
    
    args = parser.parse_args()

    # Primary particle option
    iprim=int(args.iprim)
    primary_list=(PRMPAR_PROTON,PRMPAR_HELIUM,PRMPAR_NITROGEN,PRMPAR_IRON)
    if iprim not in primary_list:
        sys.stderr.write("ERROR: primary particle ID {:d} is not one of the following: \n"\
                             .format(iprim));
        sys.stderr.write(str(primary_list)+"\n")
        sys.exit(2)
    card.set_PRMPAR(iprim)

    # Energy option (and optimal thinning, depending on the energy values)
    log10en=float(args.log10en)
    if log10en not in BTS_PAR.keys():
        sys.stderr.write("ERROR: primary particle energy {:.2f} is not one of the following: \n"\
                             .format(float(args.log10en)))
        sys.stderr.write(str(sorted(BTS_PAR.keys()))+"\n")
        sys.exit(2)
    card.set_fixed_log10en(log10en)
    par=BTS_PAR[log10en]
    energy_id=int(par[0])
    card.set_THIN(par[1],par[2],par[3])
    card.set_THINH(par[4],par[5])

  
    # Generate the same number of events as B. T. Stokes? If
    # so then set the indices to correct minimum and maximum values
    # and do not allow setting a fixed zenith angle (-the option)
    if args.BTS:
        imin = int(0)
        imax = int(par[6])-1
        # make sure that the options were used consistently
        if (args.imin or args.imax):
            sys.stderr.write("ERROR: you may not use \'-imin\' and/or \'-imax\' options together with \'-BTS\' option.\n"\
                                 .format(float(args.log10en)))
            sys.exit(2)
        if (args.theta):
            sys.stderr.write("ERROR: you may not use \'-the\' option together with \'-BTS\' option.\n"\
                                 .format(float(args.log10en)))
            sys.exit(2)

    # Otherwise, get the indices that determine how many files to generate
    # from the command line. Also, allow the option to set a fixed zenith angle
    # if the user wants to.
    else:
        if args.imin:
            imin=int(args.imin)
            if not (0 <= imin <= 9999):
                sys.stderr.write("ERROR: imin {:d} is not in 0 to 9999 range\n".format(imin))
                sys.exit(2)
        else:
            imin = int(0)
        if args.imax:
            imax=int(args.imax)
            if not (imin <= imax <= 10000):
                sys.stderr.write("ERROR: imax {:d} is not in imin ({:d}) to 9999 range\n".format(imax,imin))
                sys.exit(2)
        else:
            imax=int(0)
        # Zenith angle option
        if args.theta:
            theta=float(args.theta)
            if not (0 <= theta <= 60.0):
                sys.stderr.write("ERROR: primary particle zenith angle {:.2f} is not int 0 to 60 degree range\n"\
                                     .format(theta));
                sys.exit(2)
            card.set_fixed_theta(theta)

    # Is EPOS option on?
    if args.EPOS:
        card.add_EPOS_CARDS()

    outdir=args.outdir
    if not os.path.isdir(outdir):
        sys.stderr.write("ERROR: {:s} directory not found\n".format(outdir))
        sys.exit(2)
    outdir=os.path.abspath(outdir)

    verbosity = int(args.verbosity)
    
    # now write out CORSIKA card files, using different sets of seeds for each file
    for i in range(imin,imax+1):
        runnr=i*100+energy_id
        fname=outdir+"/"+"DAT{:06d}.in".format(runnr)
        seeds=get_5_cor_seeds()
        card.set_RUNNR(runnr)
        card.set_SEED(seeds[0],seeds[1],seeds[2],seeds[3],seeds[4])
        with open(fname,"w") as f:
            f.write(card.buf+"\n")
    if (verbosity >=1):
        if(args.EPOS):
            sys.stdout.write("EPOS ")
        sys.stdout.write("PRIMARY {:d} ENERGY {:.1f} ({:02d}): {:d} card files\n".format(iprim,log10en,energy_id,imax-imin+1))
        sys.stdout.flush()
    
if __name__ == "__main__":
    main()
