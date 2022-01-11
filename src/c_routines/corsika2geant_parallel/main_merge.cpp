#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <map>
#include <algorithm>
#include <math.h>

#include "./structs.h"
#include "./utils.h"
#include "./constants.h"

// {[x, y, t]: value}
typedef std::map<std::array<short, 3>, unsigned short> Sparse3DMatrix;
#define MAX_SPARSE3DMATRIX_SIZE ((double)NX * (double)NY * (double)TMAX) // ~10^10
#define sparse3DMatrixLoadFactor(matrix) (double)(matrix.size()) / MAX_SPARSE3DMATRIX_SIZE
#define getValueOrZero(matrix, key, assign_to) \
    if (1)                                     \
    {                                          \
        auto it = matrix.find(key);            \
        if (it == matrix.end())                \
            assign_to = 0;                     \
        else                                   \
            assign_to = it->second;            \
    }

Sparse3DMatrix vem_top;
Sparse3DMatrix vem_bot;
Sparse3DMatrix pz;

// all the time indices (k) in merged sparse array are stored relative to these times and hence can be negative
float reference_min_arrival_times[NX][NY];
float global_min_arrival_times[NX][NY];
float current_min_arrival_times[NX][NY];

void initMinArrivalTimes(float arr[NX][NY])
{
    for (short m = 0; m < NX; m++)
        for (short n = 0; n < NY; n++)
            arr[m][n] = SENTINEL_TIME;
}

bool readCurrentMinArrivalTimes(FILE *f)
{
    initMinArrivalTimes(current_min_arrival_times);
    short m;
    short n;
    float time;
    while (1)
    {
        size_t values_read = fread(&m, sizeof(short), 1, f) +
                             fread(&n, sizeof(short), 1, f) +
                             fread(&time, sizeof(float), 1, f);
        if (values_read != 3) // reached the end of the file, something's not right
            return false;
        if (m == -1) // reached delimiter triplet, read is done
            return true;
        current_min_arrival_times[m][n] = time;
        // the first min arrival time for (m, n) across all partial tile files is considered reference
        if (reference_min_arrival_times[m][n] == SENTINEL_TIME)
            reference_min_arrival_times[m][n] = time;
        if (time < global_min_arrival_times[m][n])
            global_min_arrival_times[m][n] = time;
    }
}

bool loadPartialTileFile(char *filename, EventHeaderData *event_data)
{
    fprintf(stdout, "Reading partial tile file %s\n", filename);
    FILE *fptile = fopen(filename, "r");
    if (fptile == NULL)
    {
        fprintf(stderr, "Cannot open %s: %s\n", filename, strerror(errno));
        return false;
    }

    if (!readEventHeaderData(event_data, fptile))
    {
        fprintf(stderr, "Error reading event header from %s\n", filename);
        return false;
    }

    if (!readCurrentMinArrivalTimes(fptile))
    {
        fprintf(stderr, "Error reading min arrival times from %s\n", filename);
        return false;
    }

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
    fprintf(stdout, "Writing merged tile data to %s\n", filename);
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
        if (buf[2] == 0 && buf[3] == 0)
            continue;
        // transforming # bins from min arrival time (in [0; TMAX]) to # bins from tmin
        buf[4] = (unsigned short)((reference_min_arrival_times[mnk[0]][mnk[1]] + (float)(mnk[2]) * DT - ed->tmin) / DT);
        buf[5] = pz[mnk];
        if (fwrite(buf, sizeof(short), TILE_FILE_BLOCK_SIZE, fout) != TILE_FILE_BLOCK_SIZE)
        {
            fclose(fout);
            return false;
        }
    }
    fclose(fout);
    return true;
}

float interp_radius; // m
int interp_halfside; // tiles from NX / 2

void inetrpolateMinArrivalTimes()
{
    int m_edge = NX / 2;
    while (global_min_arrival_times[m_edge][NY / 2] == SENTINEL_TIME)
        m_edge++;
    interp_radius = tileIndex2Coord(m_edge) + 2.0;
    interp_halfside = m_edge - NX / 2 + 5;
    printf("Interpolating tiles inside the %g m circle\n", interp_radius);

    for (int m = NX / 2 - interp_halfside; m < NX / 2 + interp_halfside; m++)
        for (int n = NY / 2 - interp_halfside; n < NY / 2 + interp_halfside; n++)
        {
            float x = tileIndex2Coord(m);
            float y = tileIndex2Coord(n);
            if (hypotf(x, y) < interp_radius)
            {
                float radius_ratio = (interp_radius + 7.5) / hypotf(x, y);
                // interpolated time is lerp between times at closest and farthest points on the ring
                float x_on_ring = 100 * x * radius_ratio; // m -> cm
                float y_on_ring = 100 * y * radius_ratio; // m -> cm
                int m_close = coord2TileIndex(x_on_ring);
                int n_close = coord2TileIndex(y_on_ring);
                int m_far = coord2TileIndex(-x_on_ring);
                int n_far = coord2TileIndex(-y_on_ring);
                // this is lerp, trust me...
                global_min_arrival_times[m][n] = 0.5 * (global_min_arrival_times[m_close][n_close] + global_min_arrival_times[m_far][n_far]) +
                                                 0.5 * (global_min_arrival_times[m_close][n_close] - global_min_arrival_times[m_far][n_far]) /
                                                     radius_ratio;
                reference_min_arrival_times[m][n] = global_min_arrival_times[m][n];
            }
        }
}

void interpolateTile(EventHeaderData *ed)
{
    float sectheta = 1 / cosf(ed->zenith);
    std::array<short, 3> mnk;
    std::array<short, 3> mnk_sample;
    for (mnk[0] = NX / 2 - interp_halfside; mnk[0] < NX / 2 + interp_halfside; mnk[0] += 1)
    {
        for (mnk[1] = NY / 2 - interp_halfside; mnk[1] < NY / 2 + interp_halfside; mnk[1] += 1)
        {
            float x = tileIndex2Coord(mnk[0]);
            float y = tileIndex2Coord(mnk[1]);
            float r = hypotf(x, y);
            if (r < interp_radius)
            {
                float zencor = hypotf(x / sectheta, y) / r;
                float sampling_radius = interp_radius + 7.5; // offsetting to the next non-interpolated tile
                float r_ratio = sampling_radius / r;
                mnk_sample[0] = coord2TileIndex(100 * x * r_ratio);
                mnk_sample[1] = coord2TileIndex(100 * y * r_ratio);

                // e.g. if reference min arrival time happens to be 3*DT ahead of global min, this will be -3
                short global2ref_delta_k = (short)((global_min_arrival_times[mnk_sample[0]][mnk_sample[1]] -
                                                    reference_min_arrival_times[mnk_sample[0]][mnk_sample[1]]) /
                                                   DT);

                // for interpolated tiles reference min arr. time = global min arr. time, so k starts from 0
                for (mnk[2] = 0; mnk[2] < TMAX; mnk[2] += 1)
                {
                    // interpolated k counts from 0 while sampled k -- from reference
                    mnk_sample[2] = mnk[2] + global2ref_delta_k;

                    unsigned short vem_top_sample;
                    getValueOrZero(vem_top, mnk_sample, vem_top_sample);
                    unsigned short vem_bot_sample;
                    getValueOrZero(vem_bot, mnk_sample, vem_bot_sample);

                    if (vem_top_sample == 0 && vem_bot_sample == 0)
                        continue;

                    unsigned short pz_sample;
                    getValueOrZero(pz, mnk_sample, pz_sample);

                    float vem_sample_to_interp_factor = powf(r_ratio, 2.6) * expf(zencor * (sampling_radius - r) / 575.0);

                    float vem_top_interp = std::min((float)vem_top_sample * vem_sample_to_interp_factor, (float)60000.);
                    vem_top[mnk] = (unsigned short)vem_top_interp;

                    float vem_bot_interp = std::min((float)vem_bot_sample * vem_sample_to_interp_factor, (float)60000.);
                    vem_bot[mnk] = (unsigned short)vem_bot_interp;

                    float vem_mean_sample = 0.5 * ((float)vem_top_sample + (float)vem_bot_sample);
                    float vem_mean_interp = 0.5 * (vem_top_interp + vem_bot_interp);
                    float costheta_sample = (float)pz_sample / vem_mean_sample;
                    // linear interpolation of cos theta between shower's (i.e. for particles near the core)
                    // and sample tile's (for particles sampling_radius m from the core)
                    float pz_interp = vem_mean_interp *
                                      ((r / sampling_radius) * costheta_sample +
                                       (1.0 - r / sampling_radius) * cosf(ed->zenith));
                    pz[mnk] = (unsigned short)pz_interp;
                }
            }
        }
    }
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
    initMinArrivalTimes(global_min_arrival_times);
    initMinArrivalTimes(reference_min_arrival_times);

    FILE *flist = fopen(listing_file, "r");

    fprintf(stdout, "Reading file list %s\n", listing_file);
    if (flist == NULL)
    {
        fprintf(stderr, "Cannot open file %s: %s\n", listing_file, strerror(errno));
        exit(EXIT_FAILURE);
    }

    char partial_tile_file[4096];
    while (fscanf(flist, "%s\n", partial_tile_file) != EOF)
    {
        if (!loadPartialTileFile(partial_tile_file, &event_data))
            exit(EXIT_FAILURE);
        fprintf(stdout, "Sparse matrices load (1%% ~ 600Mb RAM): %f%%\n", 100 * sparse3DMatrixLoadFactor(vem_top));
    }

    inetrpolateMinArrivalTimes();
    interpolateTile(&event_data);

    dumpTileFile(output_file, &event_data);

    fprintf(stdout, "OK\n");
    fclose(flist);
}
