#ifndef CONSTANTS_H_
#define CONSTANTS_H_

// physical constants

#define DISTMAX 8400 /* Meters / 10.0 */
#define NX DISTMAX / 3
#define NY DISTMAX / 3
#define DT 20
#define FRAC 0.99
#define EMIN 0.003
#define VEM 2.05 /* MeV */
#define SRL 0.06
#define CSPEED 29.97925 /* cm/nsec */
#define TMAX 1280
#define PI 3.14159265359

static const float pmass[26] = {0., 0., 0.511e-3, .511e-3, 0., 105.7e-3, 105.7e-3, 135.e-3,
                                140.e-3, 140.e-3, 498.e-3, 494.e-3, 494.e-3, 940.e-3, 938.e-3,
                                938.e-3, 498.e-3, 549.e-3, 1116.e-3, 1189.e-3, 1193.e-3,
                                1197.e-3, 1315.e-3, 1321.e-3, 1672e-3, 940.e-3};

// CORSIKA stuff

#define NSENTENCE 39
#define NPART 7
#define NWORD NPART *NSENTENCE
#define NSUBBLOCK 21
#define PARTSIZE 7

#define EXIT_FAILURE_DOUBLE -1.0 // replacement for EXIT_FAILURE for double-returning func

#endif
