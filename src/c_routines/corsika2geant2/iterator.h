#include "constants.h"

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
    float eventbuf[NWORD]; // event header buffer verbatim, see GUIDE p. 127
    float origin[3];       // first interaction point
    float tmin;            // from origin to the observation level
    float zenith;
} EventHeaderData;

typedef struct ParticleData
{
    // particle record verbatim:
    // 0: description; 1, 2, 3: momentum, GeV/c, 4, 5: position in observation level plane, cm; 6: t since first interaction, ns
    float partbuf[NPART];
    int id;
    float energy;
} ParticleData;

// Iterator over CORSIKA output particle file, executing a callback on each particle
// returns success flag
bool iterateParticleFile(
    const char *particle_filename, void (*processParticle)(ParticleData *), ParticleFileStats *stats, bool verbose);
