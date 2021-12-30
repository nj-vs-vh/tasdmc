#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <map>

#include "./structs.h"
#include "./constants.h"

// {[x, y, t]: value}
typedef std::map<std::array<short, 3>, unsigned short> Sparse3DMatrix;
#define MAX_SPARSE3DMATRIX_SIZE ((double)NX * (double)NY * (double)TMAX) // ~10^10
#define sparse3DMatrixLoadFactor(matrix) (double)(matrix.size()) / MAX_SPARSE3DMATRIX_SIZE
#define insertAddIfExists(matrix, key, value) if (1) { \
    auto it = matrix.find(key); \
    if (it != matrix.end()) \
        it->second += value; \
    else \
        matrix[key] = value; } 

Sparse3DMatrix vem_top;
Sparse3DMatrix vem_bot;
Sparse3DMatrix pz;

float reference_min_arrival_times[NX][NY];
float current_min_arrival_times[NX][NY];

bool readMinArrivalTimes(FILE *f, float arr[NX][NY])
{
    return (fread(arr, sizeof(float), NX * NY, f) == (NX * NY));
}

bool loadPartialTileFile(char *filename, EventHeaderData *event_data, bool initial)
{
    fprintf(stdout, "Reading partial tile file %s\n", filename);
    FILE *fptile = fopen(filename, "r");
    if (fptile == NULL)
    {
        fprintf(stderr, "Cannot open file %s: %s\n", filename, strerror(errno));
        return false;
    }

    if (!readEventHeaderData(event_data, fptile))
    {
        fprintf(stderr, "Error reading event header from partial tile file %s\n", filename);
        return false;
    }

    if (!readMinArrivalTimes(fptile, current_min_arrival_times))
    {
        fprintf(stderr, "Error reading min arrival times from partial tile file %s\n", filename);
        return false;
    }

    if (initial)
        memcpy(reference_min_arrival_times, current_min_arrival_times, NX * NY * sizeof(float));

    unsigned short buf[TILE_FILE_BLOCK_SIZE];
    std::array<short, 3> mnk;
    while (fread(buf, sizeof(short), TILE_FILE_BLOCK_SIZE, fptile) == TILE_FILE_BLOCK_SIZE)
    {
        mnk[0] = (short)buf[0];
        mnk[1] = (short)buf[1];
        // no actual rounding here because min arrival times are quantized in DT units on initial processing
        short delta_k = (short)((current_min_arrival_times[mnk[0]][mnk[1]] -
                                 reference_min_arrival_times[mnk[0]][mnk[1]]) /
                                DT);
        mnk[2] = ((short)buf[4]) + delta_k;
        unsigned short vem_top_ = buf[2];
        unsigned short vem_bot_ = buf[3];
        unsigned short pz_ = buf[5];

        // if value does not exist, the default constructor will create 0 and add new value to it
        vem_top[mnk] += vem_top_;
        vem_bot[mnk] += vem_bot_;
        pz[mnk] += pz_;
    }

    fclose(fptile);
    return true;
}

bool dumpTileFile(char *filename, EventHeaderData *ed)
{
    FILE *fout = fopen(filename, "w");
    if (fout == NULL)
    {
        fprintf(stderr, "Cannot open file %s: %s\n", filename, strerror(errno));
        return false;
    }

    if (fwrite(ed->eventbuf, sizeof(float), NWORD, fout) != NWORD)
    {
        fprintf(stderr, "Error writing event header to file: %s\n", strerror(errno));
        return false;
    }

    unsigned short buf[TILE_FILE_BLOCK_SIZE];
    std::array<short, 3> mnk;

    for (auto it = vem_top.begin(); it != vem_top.end(); ++it)
    {
        mnk = it->first;
        buf[0] = mnk[0];     // m
        buf[1] = mnk[1];     // n
        buf[2] = it->second; // vem_top
        buf[3] = vem_bot[mnk];
        // transforming # bins from min arrival time (in [0; TMAX]) to # bins from tmin
        buf[4] = (unsigned short)((reference_min_arrival_times[mnk[0]][mnk[1]] + (float)(mnk[2]) * DT - ed->tmin) / DT);
        buf[5] = pz[mnk];
        if (fwrite(buf, sizeof(short), TILE_FILE_BLOCK_SIZE, fout) != TILE_FILE_BLOCK_SIZE)
        {
            return false;
        }
    }
    fclose(fout);
    return true;
}

int main(int argc, char *argv[])
{
    if (argc != 3)
    {
        fprintf(
            stderr,
            "corsika2geant_parallel_merge.run is a routine to merge a set of partial tile files (produced with "
            "corsika2geant_parallel_partial.run) into a single tile file\n"
            "also performs interpolation of the near-axis region, masked in CORSIKA/dethinning\n\n"
            "accepts exactly 2 command line arguments:\n"
            "\ttext file listing all partial files to be merged\n"
            "\toutput tile file name\n");
        exit(EXIT_FAILURE);
    }
    const char *listing_file = argv[1];
    char *output_file = argv[2];

    EventHeaderData event_data;

    FILE *flist = fopen(listing_file, "r");

    fprintf(stdout, "Reading file list %s\n", listing_file);
    if (flist == NULL)
    {
        fprintf(stderr, "Cannot open file %s: %s\n", listing_file, strerror(errno));
        exit(EXIT_FAILURE);
    }

    char partial_tile_file[4096];
    bool initial_file = true;
    while (fscanf(flist, "%s\n", partial_tile_file) != EOF)
    {
        if (!loadPartialTileFile(partial_tile_file, &event_data, initial_file))
            exit(EXIT_FAILURE);
        initial_file = !initial_file;
        fprintf(stdout, "Sparse matrices load (1%% = about 600Mb RAM): %f%%\n", 100 * sparse3DMatrixLoadFactor(vem_top));
    }

    dumpTileFile(output_file, &event_data);

    fprintf(stdout, "OK\n");
    fclose(flist);
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
