/*
A program to produce CORSIKA particle output to tile file, holding information
about energy deposit in a tile of virtual detectors.

Based on runcorsd-old/corsika2geant.c
*/

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>

// #include "./corsika_times.h"
#include "./corsika_vem_init.h"
#include "./corsika_vem.h"
#include "./eloss_sdgeant.h"

#include "./iterator.h";
#include "./structs.h";

#include "./globals.h"
float time1[NX][NY]; // TODELETE
float eventbuf[NWORD];
float origin[3], zenith;
float tmin, filldist, emin;
int dm, dn;
unsigned short vemcount[NX][NY][NT][2];
unsigned short pz[NX][NY][NT];

// utils

int coord2TileIndex(float coord) { return (int)((coord + (float)(100 * DISTMAX)) / (TILE_SIDE * 100.0)); } // input in cm

int tileIndex2Coord(int index) { return ((float)index + 0.5) * TILE_SIDE - (float)DISTMAX; } // output in meters!!!

// particle arrival time in each tile

float minArrivalTimes[NX][NY];
#define SENTINEL_TIME 1e9
int particles_count = 0;
int outlier_particles_count = 0;

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
        particles_count++;
        m = coord2TileIndex(pd->partbuf[4]);
        n = coord2TileIndex(pd->partbuf[5]);
        if (pd->partbuf[6] < minArrivalTimes[m][n])
        {
            if (pd->partbuf[6] < sqrtf(powf(ed->origin[0] - pd->partbuf[4], 2.) +
                                       powf(ed->origin[1] - pd->partbuf[5], 2.) +
                                       powf(ed->origin[2] - observationLevel, 2.)) /
                                     CSPEED)
            {
                outlier_particles_count++;
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
    filldist = tileIndex2Coord(m_edge) + 2.0;
    int fill_tiles = m_edge - NX / 2 + 5;
    printf("Annulus Diameter: %g meters\n", filldist);

    int m_closest, m_farthest, n_closest, n_farthest;
    float x, y, x_ring_closest, y_ring_closest;
    float rad_fraction;
    for (int m = NX / 2 - fill_tiles; m < NX / 2 + fill_tiles; m++)
        for (int n = NY / 2 - fill_tiles; n < NY / 2 + fill_tiles; n++)
        {
            x = tileIndex2Coord(m);
            y = tileIndex2Coord(n);
            if (hypotf(x, y) < filldist)
            {
                rad_fraction = (filldist + 7.5) / hypotf(x, y);
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

void quantizeArrivalTimes(float t_start) {
    for (int i = 0; i < NX; i++)
        for (int j = 0; j < NY; j++)
            minArrivalTimes[i][j] = t_start + (float)DT * floorf((minArrivalTimes[i][j] - t_start) / (float)DT);
}

int main(int argc, char *argv[])
{
    // command line arguments parsing
    if (argc != 4)
    {
        fprintf(
            stderr,
            "corsika2geant (parallel) is a rewrite of corsika2geant that processes a single dethinned file and produces a 'partial' tile file\n"
            "partial tile files should then be merged together by a tile_file_merger.run\n\n"
            "accepts exactly 3 command-line arguments:\n"
            "\tdethinned CORSIKA particle file path\n"
            "\tsdgeant.dst file path\n"
            "\toutput file path\n");
        exit(EXIT_FAILURE);
    }
    const char *particle_file = argv[1];
    const char *geantFile = argv[2];
    const char *outputFile = argv[3];

    FILE *fout;
    // srand48(314159265);
    emin = 0.;

    ParticleFileStats stats;
    EventHeaderData event_data;
    initArrivalTimes();
    if (!iterateParticleFile(particle_file, &saveArrivalTime, &stats, &event_data, true))
    {
        fprintf(stderr, "minimal arrival time failed", particle_file);
        exit(EXIT_FAILURE);
    }
    fprintf(stdout, "Number of Outliers: %d\nTime of Core Impact: %g\n", outlier_particles_count, event_data.tmin);
    inetrpolateArrivalTimes();
    quantizeArrivalTimes(event_data.tmin);

    // TEMP
    FILE* ftime = fopen("time1_new.dump", "w");
    for (int m = 0; m < NX; m++)
    {
        for (int n = 0; n < NY; n++)
        {
            fwrite(&minArrivalTimes[m][n], sizeof(float), 1, ftime);
        }
    }
    fclose(ftime);

    // printf("Energy threshold: %f keV\n", emin);
    // fflush(stdout);

    // if (load_elosses(geantFile) == -1)
    // {
    //     fprintf(stderr, "Cannot open %s file\n", geantFile);
    //     exit(EXIT_FAILURE);
    // }
    // count = corsika_times(particle_file);
    // if (count == EXIT_FAILURE_DOUBLE)
    // {

    // }
    fprintf(stdout, "OK");
    exit(EXIT_SUCCESS);
}
