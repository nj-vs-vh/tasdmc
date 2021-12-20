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


// defining global variables
float min_arrival_times[NX][NY];
float interpolation_radius; // radius of area near the core that requires interpolation of values

float emin = 0.0;
int particle_count = 0;
int outlier_particle_count = 0;
int current_batch_idx = 0;


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
    srand48(314159265);

    ParticleFileStats stats;
    EventHeaderData event_data;
    initArrivalTimes();
    if (!iterateParticleFile(particle_file, &saveArrivalTime, &stats, &event_data, true))
    {
        fprintf(stderr, "minimal arrival time search failed for %s", particle_file);
        exit(EXIT_FAILURE);
    }
    fprintf(stdout, "Number of Outliers: %d\nTime of Core Impact: %g\n", outlier_particle_count, event_data.tmin);
    inetrpolateArrivalTimes();
    quantizeArrivalTimes(event_data.tmin);

    fprintf(stdout, "OK");
    exit(EXIT_SUCCESS);
}
