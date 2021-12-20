#include "./globals.h"
#include "./constants.h"
#include "./structs.h"
#include "./utils.h"
#include "./eloss_sdgeant.h"

void sumElossOnStepSaveOthers(ParticleData *pd, EventHeaderData *ed)
{
    if (!(particlePhysicalCut(pd) && particleGeometricalCut(pd)))
    {
        return;
    }
    particleCount++;
    int m = coord2TileIndex(pd->partbuf[4]);
    int n = coord2TileIndex(pd->partbuf[5]);
    // int k = (int)((buf3[6] - time1[m][n] - (float)(NT * DT * tcount)) / DT);
    float arrivalTime = pd->partbuf[6];
    int batchIdx = time2batchIdx(arrivalTime, minArrivalTimes[m][n]);
    if (batchIdx == currentBatchIdx)
    {
        int k = (int)((arrivalTime - minArrivalTimes[m][n] - (float)(T_BATCH * currentBatchIdx)) / (float)DT);
        if ((int)vemcount_top[m][n][k] < 60000 &&
            (int)vemcount_bot[m][n][k] < 60000)
        {
            double eloss_top;
            double eloss_bot;
            get_elosses(pd->id, (double)(pd->energy * 1000), (double)(pd->sectheta), &eloss_top, &eloss_bot);
            double gaussianPair[2];
            standardNormalPairBM(gaussianPair);
            eloss_top *= 1. + 0.07 * gaussianPair[0];
            eloss_bot *= 1. + 0.07 * gaussianPair[1];
            vemcount_top[m][n][k] += (unsigned short)rintf((float)eloss_top / VEM * 100.);
            vemcount_bot[m][n][k] += (unsigned short)rintf((float)eloss_bot / VEM * 100.);
            pz[m][n][k] += (unsigned short)rintf(((float)eloss_top / VEM * 100.) / pd->sectheta / 2.);
            pz[m][n][k] += (unsigned short)rintf(((float)eloss_bot / VEM * 100.) / pd->sectheta / 2.);
        }
    }
    else if (batchIdx > currentBatchIdx)
    {
        fwrite(temp_later, sizeof(float), NPART, pd->partbuf);
    }
}
