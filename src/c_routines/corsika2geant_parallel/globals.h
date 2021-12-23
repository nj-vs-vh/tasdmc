#ifndef GLOBALS_H_
#define GLOBALS_H_

#include "./constants.h"
#include <stdio.h>

// extern float eventbuf[NWORD];
// extern float origin[3], zenith;

// extern float tmin, filldist, emin;
// extern int dm, dn;
// extern unsigned short pz[NX][NY][NT];

extern float emin;
extern int particle_count;
extern int outlier_particle_count;

extern float min_arrival_times[NX][NY];
extern int current_batch_idx;
extern FILE* temp_now;
extern FILE* temp_later;

extern unsigned short vemcount[NX][NY][NT][2];
extern unsigned short pz[NX][NY][NT];

#endif
