#include <math.h>

#include "./globals.h"
#include "./constants.h"
#include "./structs.h"
#include "./utils.h"
#include "./eloss_sdgeant.h"

void initVem()
{
    for (int m = 0; m < NX; m++)
    {
        for (int n = 0; n < NY; n++)
        {
            for (int k = 0; k < NT; k++)
            {
                vemcount[m][n][k][0] = 0;
                vemcount[m][n][k][1] = 0;
                pz[m][n][k] = 0;
            }
        }
    }
}

void sumBatchElosses(ParticleData *pd, EventHeaderData *ed)
{
    if (!(particlePhysicalCut(pd, emin) && particleGeometricalCut(pd)))
    {
        return;
    }
    int m = coord2TileIndex(pd->partbuf[4]);
    int n = coord2TileIndex(pd->partbuf[5]);
    float arrival_time = pd->partbuf[6];
    int batch_idx = time2BatchIdx(arrival_time, min_arrival_times[m][n]);
    if (batch_idx == current_batch_idx)
    {
        particle_count++;
        int k = (int)((arrival_time - min_arrival_times[m][n] - (float)(T_BATCH * current_batch_idx)) / (float)DT);
        if ((int)vemcount[m][n][k][0] < 60000 &&
            (int)vemcount[m][n][k][1] < 60000)
        {
            double eloss_top;
            double eloss_bot;
            get_elosses(pd->id, (double)(pd->energy * 1000), (double)(pd->sectheta), &eloss_top, &eloss_bot);
            double normal_pair[2];
            getStandardNormalPair(normal_pair);
            float vemcount_from_particle_top = eloss2VemCount(eloss_top * (1. + 0.07 * normal_pair[0]));
            float vemcount_from_particle_bot = eloss2VemCount(eloss_bot * (1. + 0.07 * normal_pair[1]));
            vemcount[m][n][k][0] += (unsigned short)rintf(vemcount_from_particle_top);
            vemcount[m][n][k][1] += (unsigned short)rintf(vemcount_from_particle_bot);
            pz[m][n][k] += (unsigned short)rintf(0.5 * (vemcount_from_particle_top + vemcount_from_particle_bot) / pd->sectheta);
        }
    }
    else if (batch_idx > current_batch_idx)
    {
        fwrite(pd->partbuf, sizeof(float), NPART, temp_later);
    }
    else
    {
        fprintf(stdout, "OOPS");
    }
}
