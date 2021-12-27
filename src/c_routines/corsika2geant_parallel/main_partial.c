/*
A routine to convert CORSIKA particle output to a "tile file", holding information
about energy deposit in a tile of virtual detectors .
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
#include "./iterator.h"
#include "./structs.h"
#include "./globals.h"
#include "./utils.h"

#include "./arrival_times.h"
#include "./vem.h"

// defining global variables

float emin = 0.0;

float min_arrival_times[NX][NY];

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

bool dumpEventHeader(FILE *fout, EventHeaderData *ed)
{
    return (fwrite(ed->eventbuf, sizeof(float), NWORD, fout) == NWORD);
}

bool dumpMinArrivalTimes(FILE *fout)
{
    return (fwrite(min_arrival_times, sizeof(float), NX * NY, fout) == (NX * NY));
}

bool dumpVemBatch(FILE *fout, int batch_idx, EventHeaderData *event_data)
{
    // m, n, vem top, vem bot, time (DT units since shower core impact), pz
    unsigned short buf[TILE_FILE_BLOCK_SIZE];

    for (int m = 0; m < NX; m++)
    {
        for (int n = 0; n < NY; n++)
        {
            if (min_arrival_times[m][n] != SENTINEL_TIME) // there are particles in this tile at all
            {
                buf[0] = (unsigned short)m;
                buf[1] = (unsigned short)n;
                for (int k = 0; k < NT; k++)
                {
                    if (vemcount[m][n][k][0] > 0 || // at least one VEM worth of energy was deposited
                        vemcount[m][n][k][1] > 0)
                    {
                        unsigned short vem_top = vemcount[m][n][k][0];
                        unsigned short vem_bot = vemcount[m][n][k][0];
                        unsigned short pz_ = pz[m][n][k];
                        buf[2] = vem_top;
                        buf[3] = vem_bot;

                        buf[4] = (unsigned short)((min_arrival_times[m][n] + (float)(batch_idx * T_BATCH) + (float)(k * DT) - event_data->tmin) / DT);

                        if (pz_ == 0 || 2 * pz_ > vem_top + vem_bot)
                            pz_ = (unsigned short)(cosf(event_data->zenith) * (float)(vem_top + vem_bot) / 2.);
                        buf[5] = pz_;
                        if (fwrite(buf, sizeof(short), TILE_FILE_BLOCK_SIZE, fout) != TILE_FILE_BLOCK_SIZE)
                        {
                            return false;
                        }
                    }
                }
            }
        }
    }
    return true;
}

int main(int argc, char *argv[])
{
    if (argc < 4 || argc > 5)
    {
        fprintf(
            stderr,
            "corsika2geant_parallel_process.run is a rewrite of corsika2geant.run that processes a "
            "single dethinned particle file and produces a partial tile file\n"
            "partial tile files should then be merged together by corsik2geant_parallel_merge.run\n\n"
            "accepts exactly 4 command-line arguments:\n"
            "\tdethinned CORSIKA particle file path\n"
            "\tsdgeant.dst file path\n"
            "\tpartial tile file path\n"
            "\t(optional) 'signal start time per tile' file path\n");
        exit(EXIT_FAILURE);
    }
    const char *particle_file = argv[1];
    const char *sdgeant_file = argv[2];
    const char *tile_file = argv[3];
    const char *arrival_times_file = NULL;
    bool dump_min_arrival_times = (argc == 5);

    FILE *fout = fopen(tile_file, "w");
    if (!fout)
    {
        fprintf(stderr, "error creating output tile file %s", tile_file);
        return EXIT_FAILURE;
    }

    FILE *ftimes;
    if (dump_min_arrival_times)
    {
        arrival_times_file = argv[4];
        ftimes = fopen(arrival_times_file, "w");
        if (!ftimes)
        {
            fprintf(stderr, "error creating output min arrival times file %s", arrival_times_file);
            return EXIT_FAILURE;
        }
    }

    strcpy(temp_filename_1, tile_file);
    strcat(temp_filename_1, ".1.tmp");
    strcpy(temp_filename_2, tile_file);
    strcat(temp_filename_2, ".2.tmp");

    // srand48(1312);
    fprintf(stdout, "Creating %d x %d grid of tiles, each %d m in size\n", NX, NY, TILE_SIDE);

    fprintf(stdout, "Loading eloss lookup table from %s\n", sdgeant_file);
    load_elosses(sdgeant_file);

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
    if (!dumpEventHeader(fout, &event_data))
    {
        fprintf(stderr, "error writing header to output file %s", tile_file);
        exit(EXIT_FAILURE);
    }
    if (dump_min_arrival_times)
    {
        if (!dumpMinArrivalTimes(ftimes))
        {
            fprintf(stderr, "error writing min arrival times to file %s", arrival_times_file);
            return EXIT_FAILURE;
        }
        fclose(ftimes);
    }
    fprintf(stdout,
            "Particles read: %d\n... of them outliers: %d\nTime of Core Impact, ns: %g\n",
            particle_count, outlier_particle_count, event_data.tmin);
    quantizeArrivalTimes(event_data.tmin);
    int total_particle_count = particle_count;

    current_batch_idx = 0;
    fprintf(stdout, "Calculating VEM counts for %d time bins per batch for each tile\n", NT);
    prepareTempFilePointers();
    particle_count = 0;
    initVem();
    if (!iterateCorsikaParticleFile(particle_file, &sumBatchElosses, &stats, &event_data, true))
    {
        fprintf(stderr, "first elosses summation from %s failed", particle_file);
        exit(EXIT_FAILURE);
    }
    if (!dumpVemBatch(fout, current_batch_idx, &event_data))
    {
        fprintf(stderr, "error writing data (batch %d) to output file %s", current_batch_idx, tile_file);
        exit(EXIT_FAILURE);
    }

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
        if (!dumpVemBatch(fout, current_batch_idx, &event_data))
        {
            fprintf(stderr, "error writing data (batch %d) to output file %s", current_batch_idx, tile_file);
            exit(EXIT_FAILURE);
        }
        cumulative_particle_count += particle_count;
        fprintf(stdout,
                "Particles in batch %d: %d; %.4f%% processed\n",
                current_batch_idx, particle_count, 100 * (float)cumulative_particle_count / (float)total_particle_count);
    }

    fclose(temp_now);
    fclose(temp_later);
    fclose(fout);

    remove(temp_filename_1);
    remove(temp_filename_2);

    fprintf(stdout, "OK\n");
    exit(EXIT_SUCCESS);
}
