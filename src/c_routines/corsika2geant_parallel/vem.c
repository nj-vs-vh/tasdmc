#include "./globals.h"
#include "./constants.h"
#include "./structs.h"
#include "./utils.h"
#include "./eloss_sdgeant.h"

void sumBatchElosses(ParticleData *pd, EventHeaderData *ed)
{
    if (!(particlePhysicalCut(pd) && particleGeometricalCut(pd)))
    {
        return;
    }
    particle_count++;
    int m = coord2TileIndex(pd->partbuf[4]);
    int n = coord2TileIndex(pd->partbuf[5]);
    float arrival_time = pd->partbuf[6];
    int batch_idx = time2BatchIdx(arrival_time, min_arrival_times[m][n]);
    if (batch_idx == current_batch_idx)
    {
        int k = (int)((arrival_time - min_arrival_times[m][n] - (float)(T_BATCH * current_batch_idx)) / (float)DT);
        if ((int)vemcount_top[m][n][k] < 60000 &&
            (int)vemcount_bot[m][n][k] < 60000)
        {
            double eloss_top;
            double eloss_bot;
            get_elosses(pd->id, (double)(pd->energy * 1000), (double)(pd->sectheta), &eloss_top, &eloss_bot);
            double normal_pair[2];
            standardNormalPairBM(normal_pair);
            float vemc_top = eloss2VemCount(eloss_top * (1. + 0.07 * normal_pair[0]));
            float vemc_bot = eloss2VemCount(eloss_bot * (1. + 0.07 * normal_pair[1]));
            vemcount_top[m][n][k] += (unsigned short)rintf(vemc_top);
            vemcount_bot[m][n][k] += (unsigned short)rintf(vemc_bot);
            pz[m][n][k] += (unsigned short)rintf(0.5 * (vemc_top + vemc_bot) / pd->sectheta);
        }
    }
    else if (batch_idx > current_batch_idx)
    {
        fwrite(temp_later, sizeof(float), NPART, pd->partbuf);
    }
}
