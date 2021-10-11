#include "./constants.h"

float eventbuf[NWORD];
float origin[3], zenith;

float time1[NX][NY], tmin, filldist, emin;
int dm, dn;
unsigned short vemcount[NX][NY][NT][2];
unsigned short pz[NX][NY][NT];
