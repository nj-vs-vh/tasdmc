#ifndef CONSTANTS_H_
#define CONSTANTS_H_

/* 
  This variable tells how much memory to use per corsika2geant process
  (NT variable roughly equals (memory in Gb) x 16)
  One should pass -DNT=32 (or some other number) on the command line 
  when compiling the program.
*/
#ifndef NT
#error Array size variable 'NT' has not been defined. Use -DNT=16, 32, 64, etc compilation option
#endif

// physical constants and detector's tile configuration

#define MAP_SIDE 16800  // meters
#define TILE_SIDE 6  // meters
#define DISTMAX MAP_SIDE / 2 
#define NX MAP_SIDE / TILE_SIDE
#define NY MAP_SIDE / TILE_SIDE

#define SENTINEL_TIME 1e9


#define DT 20  // nanoseconds, a bin length for time quantization
#define T_BATCH DT * NT // length of time bins' batch; NT gives a number of time bins in a batch

#define VEM 2.05 /* MeV */
#define CSPEED 29.97925 /* cm/nsec */
#define TMAX 1280
#define PI 3.14159265359

static const float pmass[26] = {0., 0., 0.511e-3, .511e-3, 0., 105.7e-3, 105.7e-3, 135.e-3,
                                140.e-3, 140.e-3, 498.e-3, 494.e-3, 494.e-3, 940.e-3, 938.e-3,
                                938.e-3, 498.e-3, 549.e-3, 1116.e-3, 1189.e-3, 1193.e-3,
                                1197.e-3, 1315.e-3, 1321.e-3, 1672e-3, 940.e-3};

static const float observationLevel = 1430.e2; // cm, above sea level

// CORSIKA stuff

#define NSENTENCE 39  // particles in one data sub-block
#define NPART 7  // floats in particle record 
#define NWORD NPART *NSENTENCE
#define NSUBBLOCK 21  // data sub-blocks per block

#endif
