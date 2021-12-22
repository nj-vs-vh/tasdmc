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

#include "./eloss_sdgeant.h"
#include "./iterator.h";
#include "./structs.h";
#include "./globals.h"
#include "./utils.h"

#include "./arrival_times.h"
#include "./vem.h"

// defining global variables

float emin = 0.0;

float min_arrival_times[NX][NY];
float interpolation_radius; // radius of area near the core that requires interpolation of values

int particle_count;
int outlier_particle_count;
int current_batch_idx;

unsigned short vemcount[NX][NY][NT][2];
unsigned short pz[NX][NY][NT];

FILE *temp_now = NULL;
FILE *temp_later = NULL;
char temp_filename_1[4096];
char temp_filename_2[4096];
bool temp_files_swap = true;

void prepareTempFilePointers()
{
    if (temp_now != NULL && temp_later != NULL)
    {
        fclose(temp_now);
        fclose(temp_later);
    }
    // swapping two temp files between "now" and "later" roles on each function call
    const char *now_filename = temp_files_swap ? temp_filename_1 : temp_filename_2;
    const char *later_filename = temp_files_swap ? temp_filename_2 : temp_filename_1;
    temp_now = fopen(now_filename, "r");
    temp_later = fopen(later_filename, "w");
    temp_files_swap = !temp_files_swap;
}

int main(int argc, char *argv[])
{
    // command line arguments parsing
    if (argc != 4)
    {
        fprintf(
            stderr,
            "corsika2geant (parallel) is a rewrite of corsika2geant that processes a single dethinned file and produces a 'partial' tile file\n"
            "partial tile files should then be merged together\n\n"
            "accepts exactly 3 command-line arguments:\n"
            "\tdethinned CORSIKA particle file path\n"
            "\tsdgeant.dst file path\n"
            "\toutput file path\n");
        exit(EXIT_FAILURE);
    }
    const char *particle_file = argv[1];
    const char *geantFile = argv[2];
    const char *outputFile = argv[3];

    strcpy(temp_filename_1, outputFile);
    strcat(temp_filename_1, ".1.tmp");
    strcpy(temp_filename_2, outputFile);
    strcat(temp_filename_2, ".2.tmp");

    FILE *fout;
    srand48(314159265);

    fprintf(stdout, "Creating %d x %d grid of tiles, each %d m in size\n", NX, NY, TILE_SIDE);

    fprintf(stdout, "Loading eloss lookup table from %s\n", geantFile);
    load_elosses(geantFile);

    ParticleFileStats stats;
    EventHeaderData event_data;
    fprintf(stdout, "Calculating minimum particle arrival time for each tile\n");
    initArrivalTimes();
    particle_count = 0;
    outlier_particle_count = 0;
    if (!iterateCorsikaParticleFile(particle_file, &saveArrivalTime, &stats, &event_data, true))
    {
        fprintf(stderr, "minimal arrival time calculation failed for %s", particle_file);
        exit(EXIT_FAILURE);
    }
    fprintf(stdout,
            "Particles read: %d\n... of them outliers: %d\nTime of Core Impact, ns: %g\n\n",
            particle_count, outlier_particle_count, event_data.tmin);
    inetrpolateArrivalTimes();
    quantizeArrivalTimes(event_data.tmin);
    int total_particle_count = particle_count;

    current_batch_idx = 0;
    fprintf(stdout, "Calculating VEM counts for time bins in the first batch (%d bins) for each tile\n", NT);
    prepareTempFilePointers();
    particle_count = 0;
    initVem();
    if (!iterateCorsikaParticleFile(particle_file, &sumBatchElosses, &stats, &event_data, true))
    {
        fprintf(stderr, "first elosses summation from %s failed", particle_file);
        exit(EXIT_FAILURE);
    }
    interpolateVemCounts(&event_data);
    int cumulative_particle_count = particle_count;
    fprintf(stdout,
                "Particles in batch %d: %d; %.4f%% processed\n",
                current_batch_idx, particle_count, 100 * (float)cumulative_particle_count / (float)total_particle_count);

    for (current_batch_idx = 1; current_batch_idx < (int)ceilf((float)TMAX / (float)NT); current_batch_idx++)
    {
        prepareTempFilePointers();
        particle_count = 0;
        initVem();
        iteratePlainParticleFile(temp_now, &sumBatchElosses, &event_data);
        interpolateVemCounts(&event_data);
        cumulative_particle_count += particle_count;
        fprintf(stdout,
                "Particles in batch %d: %d; %.4f%% processed\n",
                current_batch_idx, particle_count, 100 * (float)cumulative_particle_count / (float)total_particle_count);
    }

    fclose(temp_now);
    fclose(temp_later);

    fprintf(stdout, "OK");
    exit(EXIT_SUCCESS);
}
