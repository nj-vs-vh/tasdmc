#include <math.h>
#include "stdbool.h"

#include "./structs.h"
#include "./globals.h"

bool particleGeometricalCut(ParticleData *pd)
{
    return fabsf(pd->partbuf[4]) < (float)(100 * DISTMAX) && fabsf(pd->partbuf[5]) < (float)(100 * DISTMAX) && pd->partbuf[6] > 1.e4;
}

bool particlePhysicalCut(ParticleData *pd)
{
    return pd->id >= 1 && pd->id < 26 && pd->energy > emin / 1.e6;
}
