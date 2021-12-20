/*
A helper file defining structs incapsulating data read from CORSIKA
files and some common operations on them
*/

#ifndef STRUCTS_H_
#define STRUCTS_H_

#include "constants.h"
#include <stdbool.h>

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
    float eventbuf[NWORD]; // event header buffer verbatim, see CORSIKA GUIDE p. 127
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
bool particlePhysicalCut(ParticleData* pd);

#endif