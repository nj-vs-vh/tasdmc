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

#define SINSITIVE_SQUARE_SIDE 16800  // meters/10 (??? probably just meters???)
#define TILE_SIDE 6  // meters
#define DISTMAX SINSITIVE_SQUARE_SIDE / 2 
#define NX SINSITIVE_SQUARE_SIDE / TILE_SIDE
#define NY SINSITIVE_SQUARE_SIDE / TILE_SIDE

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

static const float observationLevel = 1430.e2; // cm, above sea level

// CORSIKA stuff

#define NSENTENCE 39  // particles in one data sub-block
#define NPART 7  // floats in particle record 
#define NWORD NPART *NSENTENCE
#define NSUBBLOCK 21  // data sub-blocks per block

#define EXIT_FAILURE_DOUBLE -1.0 // replacement for EXIT_FAILURE for double-returning func

#endif
