#include "./globals.h"
#include "./constants.h"
#include "./structs.h"
#include "./utils.h"
#include "./eloss_sdgeant.h"

void initVem()
{
    for (int i = 0; i < NX; i++)
    {
        for (int j = 0; j < NY; j++)
        {
            for (int k = 0; k < NT; k++)
            {
                vemcount[i][j][k][0] = 0;
                vemcount[i][j][k][1] = 0;
                pz[i][j][k] = 0;
            }
        }
    }
}

void sumBatchElosses(ParticleData *pd, EventHeaderData *ed)
{
    if (!(particlePhysicalCut(pd) && particleGeometricalCut(pd)))
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
            standardNormalPairBM(normal_pair);
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
}

void interpolateVemCounts(EventHeaderData *ed)
{
    float sectheta = 1 / cosf(ed->zenith);
    int d_idx = coord2TileIndex(interpolation_radius) + 1;
    for (int m = NX / 2 - d_idx; m < NX / 2 + d_idx; m++)
    {
        for (int n = NY / 2 - d_idx; n < NY / 2 + d_idx; n++)
        {
            float x = tileIndex2Coord(m);
            float y = tileIndex2Coord(n);
            float radius = hypotf(x, y);
            float zencor = hypotf(x / sectheta, y) / radius;
            if (radius < interpolation_radius)
            {
                float sampling_radius = interpolation_radius + 7.5; // offsetting to the next non-interpolated tile
                float radius_frac = sampling_radius / radius;
                int m_sample = coord2TileIndex(x * radius_frac);
                int n_sample = coord2TileIndex(y * radius_frac);
                for (int i = 0; i < NT; i++)
                {
                    for (int j = 0; j < 2; j++)
                    {
                        float vem_tmp =
                            (float)vemcount[m_sample][n_sample][i][j] *
                            powf(radius_frac, 2.6) *
                            expf(zencor * (sampling_radius - radius) / 575.0);
                        if (vem_tmp > 60000.)
                            vem_tmp = 60000.;
                        vemcount[m][n][i][j] = (unsigned short)vem_tmp;
                    }

                    float vemcount_sample_mean = 0.5 * ((float)vemcount[m_sample][n_sample][i][0] +
                                                        (float)vemcount[m_sample][n_sample][i][1]);
                    float vemcount_mean = 0.5 * ((float)vemcount[m][n][i][0] +
                                                 (float)vemcount[m][n][i][1]);
                    float costheta_sample = (float)pz[m_sample][n_sample][i] / vemcount_sample_mean;
                    // linear interpolation of cos theta between shower's (= particles near the core)
                    // and sample tile's (particles sampling_radius m from the core)
                    float pz_tmp = ((radius / sampling_radius) * costheta_sample +
                                    (1.0 - radius / sampling_radius) * cosf(ed->zenith)) *
                                   vemcount_mean;
                    pz[m][n][i] = (unsigned short)pz_tmp;
                }
            }
        }
    }
}
