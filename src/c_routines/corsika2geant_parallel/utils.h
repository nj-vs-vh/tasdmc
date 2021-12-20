#ifndef UTILS_H_
#define UTILS_H_

int coord2TileIndex(float coord);
int tileIndex2Coord(int index);
void standardNormalPairBM(double pair[2]);
int time2batchIdx(float time, float startTime);

#endif