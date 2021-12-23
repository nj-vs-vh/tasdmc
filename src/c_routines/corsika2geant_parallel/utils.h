#ifndef UTILS_H_
#define UTILS_H_

#include "./constants.h"


// input in cm, as read from CORSIKA particle file
#define coord2TileIndex(coord) (int)((coord / 100.0 + (float)(DISTMAX)) / TILE_SIDE)

// output in m
#define tileIndex2Coord(idx) (((float)(idx) + 0.5) * TILE_SIDE) - (float)(DISTMAX)

#define time2BatchIdx(time, start_time) (int)(time - start_time) / (int)(T_BATCH)

#define eloss2VemCount(eloss) 100 * (float)(eloss) / VEM

void getStandardNormalPair(double pair[2]);

#endif