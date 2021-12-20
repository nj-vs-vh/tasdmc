#include "./constants.h"
#include <stdio.h>

// extern float eventbuf[NWORD];
// extern float origin[3], zenith;

// extern float tmin, filldist, emin;
// extern int dm, dn;
// extern unsigned short vemcount[NX][NY][NT][2];
// extern unsigned short pz[NX][NY][NT];

extern float emin;
extern int particleCount = 0;
extern int outlierParticleCount = 0;

extern float interpolationRadius;

extern float minArrivalTimes[NX][NY];
extern int currentBatchIdx;
extern FILE* temp_now;
extern FILE* temp_later;

extern unsigned short vemcount_top[NX][NY][NT];
extern unsigned short vemcount_bot[NX][NY][NT];
extern unsigned short pz[NX][NY][NT];

