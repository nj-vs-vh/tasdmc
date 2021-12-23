#include <math.h>

#include "./constants.h"
#include "./globals.h"
#include "./structs.h"
#include "./utils.h"

void initArrivalTimes()
{
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            min_arrival_times[i][j] = SENTINEL_TIME;
}

void saveArrivalTime(ParticleData *pd, EventHeaderData *ed)
{
    int m, n;
    if (particlePhysicalCut(pd, emin) && particleGeometricalCut(pd))
    {
        particle_count++;
        m = coord2TileIndex(pd->partbuf[4]);
        n = coord2TileIndex(pd->partbuf[5]);
        if (pd->partbuf[6] < min_arrival_times[m][n])
        {
            if (pd->partbuf[6] < sqrtf(powf(ed->origin[0] - pd->partbuf[4], 2.) +
                                       powf(ed->origin[1] - pd->partbuf[5], 2.) +
                                       powf(ed->origin[2] - observationLevel, 2.)) /
                                     CSPEED)
            {
                outlier_particle_count++;
            }
            else
            {
                min_arrival_times[m][n] = pd->partbuf[6];
            }
        }
    }
};

void quantizeArrivalTimes(float t_start)
{
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            min_arrival_times[i][j] = t_start + (float)DT * floorf((min_arrival_times[i][j] - t_start) / (float)DT);
}
