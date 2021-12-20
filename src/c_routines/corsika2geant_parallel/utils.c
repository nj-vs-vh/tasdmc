#include "./constants.h"

int coord2TileIndex(float coord) // input in cm
{
    return (int)((coord + (float)(100 * DISTMAX)) / (TILE_SIDE * 100.0));
}

int tileIndex2Coord(int index) // output in meters!
{
    return ((float)index + 0.5) * TILE_SIDE - (float)DISTMAX;
}

int time2batchIdx(float time, float startTime) {
    return (int)(time - startTime) / T_BATCH;
}

void standardNormalPairBM(double pair[2]) // Box-Muller method
{
    double r, phi;
    r = sqrt(-2.0 * log(drand48()));
    phi = 2 * PI * drand48();
    pair[0] = (r * cos(phi));
    pair[1] = (r * sin(phi));
}
