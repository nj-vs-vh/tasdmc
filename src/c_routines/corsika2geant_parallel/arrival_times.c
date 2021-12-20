#include "./constants.h"
#include "./globals.h"
#include "./structs.h"


void initArrivalTimes()
{
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            minArrivalTimes[i][j] = SENTINEL_TIME;
}

void saveArrivalTime(ParticleData *pd, EventHeaderData *ed)
{
    int m, n;
    if (particlePhysicalCut(pd) && particleGeometricalCut(pd))
    {
        particleCount++;
        m = coord2TileIndex(pd->partbuf[4]);
        n = coord2TileIndex(pd->partbuf[5]);
        if (pd->partbuf[6] < minArrivalTimes[m][n])
        {
            if (pd->partbuf[6] < sqrtf(powf(ed->origin[0] - pd->partbuf[4], 2.) +
                                       powf(ed->origin[1] - pd->partbuf[5], 2.) +
                                       powf(ed->origin[2] - observationLevel, 2.)) /
                                     CSPEED)
            {
                outlierParticleCount++;
            }
            else
            {
                minArrivalTimes[m][n] = pd->partbuf[6];
            }
        }
    }
};

void inetrpolateArrivalTimes()
{
    int m_edge = NX / 2;
    while (minArrivalTimes[m_edge][NY / 2] == SENTINEL_TIME)
        m_edge++;
    interpolationRadius = tileIndex2Coord(m_edge) + 2.0;
    int fill_tiles = m_edge - NX / 2 + 5;
    printf("Annulus Diameter: %g meters\n", interpolationRadius);

    int m_closest, m_farthest, n_closest, n_farthest;
    float x, y, x_ring_closest, y_ring_closest;
    float rad_fraction;
    for (int m = NX / 2 - fill_tiles; m < NX / 2 + fill_tiles; m++)
        for (int n = NY / 2 - fill_tiles; n < NY / 2 + fill_tiles; n++)
        {
            x = tileIndex2Coord(m);
            y = tileIndex2Coord(n);
            if (hypotf(x, y) < interpolationRadius)
            {
                rad_fraction = (interpolationRadius + 7.5) / hypotf(x, y);
                x_ring_closest = 100 * x * rad_fraction; // m -> cm
                y_ring_closest = 100 * y * rad_fraction; // m -> cm
                m_closest = coord2TileIndex(x_ring_closest);
                n_closest = coord2TileIndex(y_ring_closest);
                m_farthest = coord2TileIndex(-x_ring_closest);
                n_farthest = coord2TileIndex(-y_ring_closest);
                minArrivalTimes[m][n] = 0.5 * (minArrivalTimes[m_closest][n_closest] + minArrivalTimes[m_farthest][n_farthest]);
                minArrivalTimes[m][n] += (minArrivalTimes[m_closest][n_closest] - minArrivalTimes[m_farthest][n_farthest]) /
                                         rad_fraction /
                                         2.0;
            }
        }
}

void quantizeArrivalTimes(float t_start)
{
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            minArrivalTimes[i][j] = t_start + (float)DT * floorf((minArrivalTimes[i][j] - t_start) / (float)DT);
}
