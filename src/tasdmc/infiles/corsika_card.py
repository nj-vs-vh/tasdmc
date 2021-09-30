"""Based on corcard.py script, repurposed for use as a module"""

import re
import math
import getpass
import random
from pathlib import Path
import click

from typing import Optional

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


LOG10_E_STEP = 0.1
LOG10_E_MIN_POSSIBLE = min(BTS_PAR.keys())
LOG10_E_MAX_POSSIBLE = max(BTS_PAR.keys()) + LOG10_E_STEP


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


# CORSIKA version 73695 allows random integer seeds in 1,900000000 range
# inclusively.  Getting an ntuple of 5 random seeds.
def get_5_cor_seeds():
    return tuple([random.randint(1, 900000000) for _ in range(5)])


class CorsikaCard:

    def __init__(self):
        self.buf=BTS_SAMPLE_CARD_FILE.strip()
        self.epos_cards_added=False

    def replace_card(self, card_name, card_value, occurrence=1):

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
        crd_replaced=r'{:s} {:s}'.format(name, value)
        self.buf = re.sub(crd_original, Nth(occurrence, occurrence, crd_replaced), self.buf)

    def set_RUNNR(self,runnr):
        self.replace_card("RUNNR","{:06d}".format(runnr))

    def set_ATMOD(self,atmod):
        self.replace_card("ATMOD","{:d}".format(atmod))

    def set_PRMPAR(self,prmpar):
        self.replace_card("PRMPAR","{:d}".format(prmpar))

    def set_fixed_log10en(self,log10en_eV):
        E_GeV=1e-9*math.pow(10.0,float(log10en_eV))
        val="{:.6E} {:.6E}".format(E_GeV,E_GeV).replace("+0","+")
        self.replace_card("ERANGE", val)

    def set_fixed_theta(self,theta_deg):
        self.replace_card("THETAP", "{:.2f} {:.2f}".format(theta_deg,theta_deg))
    
    def set_fixed_phi(self,phi_deg):
        self.replace_card("PHIP", "{:.2f} {:.2f}".format(phi_deg,phi_deg))

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
        self.replace_card("SEED", "{:d} 0 0".format(seed1), occurrence=1)
        self.replace_card("SEED", "{:d} 0 0".format(seed2), occurrence=2)
        self.replace_card("SEED", "{:d} 0 0".format(seed3), occurrence=3)
        self.replace_card("SEED", "{:d} 0 0".format(seed4), occurrence=4)
        self.replace_card("SEED", "{:d} 0 0".format(seed5), occurrence=5)

    def set_USER(self,user):
        self.replace_card("USER",user)
        
    def set_HOST(self,host):
        self.replace_card("HOST",host)
        
    def add_EPOS_CARDS(self):
        if not self.epos_cards_added:
            self.buf = self.buf + "\n" + EPOS_CARDS.strip()
            self.epos_cards_added=True
        

def generate_corsika_cards(
    primary_particle_id: int,
    log10_E_primary: float,
    is_epos: bool,
    is_urqmd: bool,
    output_dir: Path,
    event_number_multiplier: float = 1.0,
    event_number_override: Optional[int] = None,
    fixed_theta_angle: Optional[float] = None,
    verbose: bool = False,
):
    card = CorsikaCard()
    card.set_USER(getpass.getuser());
    card.set_HOST("chpc")
    card.set_PRMPAR(primary_particle_id)

    log10_E_options = list(BTS_PAR.keys())
    _log10_E_residuals = [abs(log10_E_option - log10_E_primary) for log10_E_option in log10_E_options]
    closest_option_idx = _log10_E_residuals.index(min(_log10_E_residuals))

    log10_E_primary_quantized = log10_E_options[closest_option_idx]
    card.set_fixed_log10en(log10_E_primary_quantized)

    # thinning options optimal for the energy
    par=BTS_PAR[log10_E_primary_quantized]
    energy_id=int(par[0])
    card.set_THIN(par[1],par[2],par[3])
    card.set_THINH(par[4],par[5])

    if event_number_override is None:
        # number of events for each energy was heuristically selected by B.T. Stokes and is used here
        min_file_index = int(0)
        max_file_index = int(par[6] * event_number_multiplier) - 1
        if not 0 <= max_file_index <= 9999:
            raise ValueError(
                f"Event number multiplier {event_number_multiplier} results in file index exceeding "
                + f"9999, select smaller value (event number without multiplication = {par[6]})."
            )
    else:
        min_file_index = int(0)
        max_file_index=int(event_number_override)
        if not 0 <= max_file_index <= 9999:
            raise ValueError(f"Overriden event number ({event_number_override}) exceeds 9999")
        if fixed_theta_angle is not None:
            if not (0 <= fixed_theta_angle <= 60.0):
                raise ValueError(f"Fixed theta angle = {fixed_theta_angle:.2f}, outside allowed 0 - 60 degrees range")
            card.set_fixed_theta(fixed_theta_angle)

    if is_epos:
        card.add_EPOS_CARDS()

    # if low-energy hadronic interaction model is URQMD, E cut must be higher (0.05 GeV -> 0.3 GeV)
    if is_urqmd:
        card.replace_card("ECUTS", "0.3  0.05  0.00025  0.00025")

    for file_index in range(min_file_index, max_file_index+1):
        runnr = file_index*100 + energy_id
        card_file = output_dir / f"DAT{runnr:06d}.in"
        card.set_RUNNR(runnr)
        card.set_SEED(*get_5_cor_seeds())  # new seeds are generated for each card
        with open(card_file, "w") as f:
            f.write(card.buf+"\n")

    if verbose:
        click.secho(
            f"PRIMARY {primary_particle_id:d} ENERGY {log10_E_primary_quantized:.1f} ({energy_id:02d}){' EPOS' if is_epos else ''}: "
            f"{max_file_index-min_file_index+1:d} card files",
            dim=True,
        )
