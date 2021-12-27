/*
A helper file defining structs incapsulating data read from CORSIKA
files and some common operations on them
*/

#ifndef STRUCTS_H_
#define STRUCTS_H_

#include <stdbool.h>

#include "./constants.h"

typedef struct ParticleFileStats
{
    int nRUNH;
    int nRUNE;
    int nEVTH;
    int nEVTE;
    int nLONG;
    int nPARTSUB;
    int n_blocks_total;
} ParticleFileStats;

typedef struct EventHeaderData
{
    /* CORSIKA event header verbatim, see CORSIKA GUIDE p. 127:
        Some useful fields:
        2 - particle ID
        3 - energy in GeV
        10 - theta (zenith) angle
    */
    float eventbuf[NWORD];
    float origin[3];       // first interaction point (?)
    float tmin;            // from origin to the observation level along shower axis with the speed of light
    float zenith;
} EventHeaderData;

typedef struct ParticleData
{
    /*  particle record verbatim:
        0: description; 1, 2, 3: momentum, GeV/c;
        4, 5: position in observation level plane, cm; 6: t since first interaction, ns
    */
    float partbuf[NPART];
    int id;
    float energy;  // in GeV
    float sectheta;
} ParticleData;

bool particleGeometricalCut(ParticleData* pd);

bool particlePhysicalCut(ParticleData *pd, float emin);

bool readEventHeaderData(EventHeaderData *d, FILE *file);

bool readParticleData(ParticleData *pd, FILE *file);

void initParticleFileStats(ParticleFileStats *s);


#endif
