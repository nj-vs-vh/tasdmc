#include <stdlib.h>
#include <stdio.h>

#include "./constants.h"


int main(int argc, char *argv[])
{
    if (argc != 4)
    {
        fprintf(
            stderr,
            "corsika2geant_parallel_merge.run is ...");
        exit(EXIT_FAILURE);
    }
    const char *particle_file = argv[1];
    const char *sdgeant_file = argv[2];
    const char *output_file = argv[3];
}

// void inetrpolateArrivalTimes()
// {
//     int m_edge = NX / 2;
//     while (min_arrival_times[m_edge][NY / 2] == SENTINEL_TIME)
//         m_edge++;
//     interpolation_radius = tileIndex2Coord(m_edge) + 2.0;
//     interpolation_tiles = m_edge - NX / 2 + 5;
//     printf("Inner circle (interpolation area) radius: %g m\n", interpolation_radius);

//     int m_closest, m_farthest, n_closest, n_farthest;
//     float x, y, x_ring_closest, y_ring_closest;
//     float rad_fraction;
//     for (int m = NX / 2 - interpolation_tiles; m < NX / 2 + interpolation_tiles; m++)
//         for (int n = NY / 2 - interpolation_tiles; n < NY / 2 + interpolation_tiles; n++)
//         {
//             x = tileIndex2Coord(m);
//             y = tileIndex2Coord(n);
//             if (hypotf(x, y) < interpolation_radius)
//             {
//                 rad_fraction = (interpolation_radius + 7.5) / hypotf(x, y);
//                 x_ring_closest = 100 * x * rad_fraction; // m -> cm
//                 y_ring_closest = 100 * y * rad_fraction; // m -> cm
//                 m_closest = coord2TileIndex(x_ring_closest);
//                 n_closest = coord2TileIndex(y_ring_closest);
//                 m_farthest = coord2TileIndex(-x_ring_closest);
//                 n_farthest = coord2TileIndex(-y_ring_closest);
//                 min_arrival_times[m][n] = 0.5 * (min_arrival_times[m_closest][n_closest] + min_arrival_times[m_farthest][n_farthest]);
//                 min_arrival_times[m][n] += (min_arrival_times[m_closest][n_closest] - min_arrival_times[m_farthest][n_farthest]) /
//                                            rad_fraction /
//                                            2.0;
//             }
//         }
// }



// void interpolateVemCounts(EventHeaderData *ed)
// {
//     float sectheta = 1 / cosf(ed->zenith);
//     for (int m = NX / 2 - interpolation_tiles; m < NX / 2 + interpolation_tiles; m++)
//     {
//         for (int n = NY / 2 - interpolation_tiles; n < NY / 2 + interpolation_tiles; n++)
//         {
//             float x = tileIndex2Coord(m);
//             float y = tileIndex2Coord(n);
//             float radius = hypotf(x, y);
//             float zencor = hypotf(x / sectheta, y) / radius;
//             if (radius < interpolation_radius)
//             {
//                 float sampling_radius = interpolation_radius + 7.5; // offsetting to the next non-interpolated tile
//                 float radius_frac = sampling_radius / radius;
//                 int m_sample = coord2TileIndex(100 * x * radius_frac);
//                 int n_sample = coord2TileIndex(100 * y * radius_frac);
//                 for (int k = 0; k < NT; k++)
//                 {
//                     for (int l = 0; l < 2; l++)
//                     {
//                         float vem_tmp =
//                             (float)vemcount[m_sample][n_sample][k][l] *
//                             powf(radius_frac, 2.6) *
//                             expf(zencor * (sampling_radius - radius) / 575.0);
//                         if (vem_tmp > 60000.)
//                             vem_tmp = 60000.;
//                         vemcount[m][n][k][l] = (unsigned short)vem_tmp;
//                     }

//                     float vemcount_sample_mean = 0.5 * ((float)vemcount[m_sample][n_sample][k][0] +
//                                                         (float)vemcount[m_sample][n_sample][k][1]);
//                     float vemcount_mean = 0.5 * ((float)vemcount[m][n][k][0] +
//                                                  (float)vemcount[m][n][k][1]);
//                     float costheta_sample = (float)pz[m_sample][n_sample][k] / vemcount_sample_mean;
//                     // linear interpolation of cos theta between shower's (= particles near the core)
//                     // and sample tile's (particles sampling_radius m from the core)
//                     float pz_ = vemcount_mean *
//                                 ((radius / sampling_radius) * costheta_sample +
//                                  (1.0 - radius / sampling_radius) * cosf(ed->zenith));
//                     pz[m][n][k] = (unsigned short)pz_;
//                 }
//             }
//         }
//     }
// }
