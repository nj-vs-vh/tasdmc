#include "./constants.h"

int coord2TileIndex(float coord) // input in cm
{
    return (int)((coord + (float)(100 * DISTMAX)) / (TILE_SIDE * 100.0));
}

int tileIndex2Coord(int index) // output in meters!
{
    return ((float)index + 0.5) * TILE_SIDE - (float)DISTMAX;
}
