/*
 * eloss_sdgeant.h
 *
 *  Last update: Apr 19, 2010
 *      Author: Dmitri Ivanov <ivanov@physics.rutgers.edu>
 */

#ifndef ELOSS_SDGEANT_H_
#define ELOSS_SDGEANT_H_

// This energy deposit (came out the same in upper and lower)
// of a vertical  300 MeV mu+ is obtained by
// fitting the two 1D histograms of upper and lower layers into
// Landau distribution and taking the most probable values.
#define VEM_MEV 2.05

////////////// FUNCTION PROTOTYPES ////////////////////

// geantfname: name of the geant DST file that stores the energy loss histograms
// 0 - success, -1 - problems
int load_elosses (char *geantfname);

// free the memory if the program needs to proceed further w/o using the geant sampler
void unload_elosses();


// corid:       corsika ID for the particle
// ke:          particle kinetic energy, in MeV
// sectheta:    ... sec(theta) of the particle
// eLossLower,
// eLossUpper:  energy losses in MeV
// 0 - success, -1 - problems
int get_elosses (int corid, double ke, double sectheta,
     double *eLossUpper, double *eLossLower);


#endif /* ELOSS_SDGEANT_H_ */
