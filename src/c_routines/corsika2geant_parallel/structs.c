#include <math.h>
#include <stdio.h>

#include "./structs.h"

bool particleGeometricalCut(ParticleData *pd)
{
    return (
        fabsf(pd->partbuf[4]) < (float)(100 * DISTMAX) &&
        fabsf(pd->partbuf[5]) < (float)(100 * DISTMAX) &&
        pd->partbuf[6] > 1.e4);
}

bool particlePhysicalCut(ParticleData *pd, float emin)
{
    return pd->id >= 1 && pd->id < 26 && pd->energy > emin / 1.e6;
}


bool readEventHeaderData(EventHeaderData *d, FILE *file)
{
    if (fread(d->eventbuf, sizeof(float), NWORD, file) != NWORD)
    {
        return false;
    }
    d->origin[0] = -d->eventbuf[7] / d->eventbuf[9] * (d->eventbuf[6] - observationLevel);
    d->origin[1] = -d->eventbuf[8] / d->eventbuf[9] * (d->eventbuf[6] - observationLevel);
    d->origin[2] = d->eventbuf[6];
    d->tmin = hypotf(hypotf(d->origin[0], d->origin[1]), d->origin[2] - observationLevel) / CSPEED;
    d->zenith = d->eventbuf[10];
    return true;
}

bool readParticleData(ParticleData *pd, FILE *file)
{
    if (fread(pd->partbuf, sizeof(float), NPART, file) != NPART)
    {
        return false;
    }
    pd->id = (int)pd->partbuf[0] / 1000.0;
    float p = hypotf(pd->partbuf[3], hypotf(pd->partbuf[1], pd->partbuf[2]));
    float mass = pmass[pd->id];
    pd->energy = hypotf(mass, p) - mass;
    pd->sectheta = p / pd->partbuf[3];
    return true;
}

void initParticleFileStats(ParticleFileStats *s)
{
    s->nRUNH = 0;
    s->nRUNE = 0;
    s->nEVTH = 0;
    s->nEVTE = 0;
    s->nLONG = 0;
    s->nPARTSUB = 0;
    s->n_blocks_total = 0;
}
