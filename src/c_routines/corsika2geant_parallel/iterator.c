#include <stdio.h>
#include <math.h>
#include <sys/types.h>
#include <libgen.h>
#include <errno.h>
#include <stdbool.h>
#include <string.h>

#include "./globals.h"
#include "./iterator.h"

// Generic iterator over CORSIKA particle file, executing a callback on each particle; returns success flag
bool iterateCorsikaParticleFile(
    const char *particle_filename,
    void (*processParticle)(ParticleData *, EventHeaderData *),
    ParticleFileStats *stats,
    EventHeaderData *event_header_data,
    bool verbose)
{
    initParticleFileStats(stats);
    ParticleData particle_data;

    const off_t RB = sizeof(float);
    int blocklen;
    float buf[NWORD];
    char block_name[5], block_name_buf[4];

    FILE *fparticle;
    if ((fparticle = fopen(particle_filename, "rb")) == NULL)
    {
        fprintf(stderr, "Cannot open %s file \n", particle_filename);
        return false;
    }
    if (verbose)
    {
        fprintf(stdout, "\tOpening %s file\n", particle_filename);
    }
    while (fread(&blocklen, sizeof(int), 1, fparticle))
    {
        stats->n_blocks_total++;
        for (int iSubblock = 0; iSubblock < NSUBBLOCK; iSubblock++)
        {
            fread(block_name_buf, sizeof(char), 4, fparticle);
            fseeko(fparticle, -RB, SEEK_CUR);
            strncpy(block_name, block_name_buf, 4);
            block_name[4] = '\0';
            if (!strcmp("RUNH", block_name))
            {
                stats->nRUNH++;
                fread(buf, sizeof(float), NWORD, fparticle);
            }
            else if (!strcmp("EVTH", block_name))
            {
                stats->nEVTH++;
                if (!readEventHeaderData(event_header_data, fparticle))
                {
                    fprintf(stderr, "Can't read header data block from %s", particle_filename);
                    return false;
                }
            }
            else if (!strcmp("LONG", block_name))
            {
                stats->nLONG++;
                fread(buf, sizeof(float), NWORD, fparticle);
            }
            else if (!strcmp("EVTE", block_name))
            {
                stats->nEVTE++;
                fread(buf, sizeof(float), NWORD, fparticle);
            }
            else if (!strcmp("RUNE", block_name))
            {
                stats->nRUNE++;
                fread(buf, sizeof(float), NWORD, fparticle);
            }
            else
            {
                for (int i_part_subblock = 0; i_part_subblock < NSENTENCE; i_part_subblock++)
                {
                    stats->nPARTSUB++;
                    if (!readParticleData(&particle_data, fparticle))
                    {
                        fprintf(stderr, "Can't read %d-th particle subblock from %s", i_part_subblock, particle_filename);
                        return false;
                    }
                    processParticle(&particle_data, event_header_data);
                }
            }
        }
        fread(&blocklen, sizeof(int), 1, fparticle);
    }
    fclose(fparticle);
    if (verbose)
    {
        printf("\tread %d blocks\n", stats->n_blocks_total);
        printf(
            "\tRUNH: %d, EVTH: %d, PARTSUB: %d, LONG: %d, EVTE: %d, RUNE: %d\n",
            stats->nRUNH, stats->nEVTH, stats->nPARTSUB, stats->nLONG, stats->nEVTE, stats->nRUNE);
    }
    return true;
}

// Same as CORSIKA particle file, but stripped of all the headers and non-particle data,
// contains a sequence of 7 float particle blocks
void iteratePlainParticleFile(
    FILE *plain_particle_stream,
    void (*processParticle)(ParticleData *, EventHeaderData *),
    EventHeaderData *event_header_data // just passed through to the callback, not modified
)
{
    ParticleData particle_data;
    while (readParticleData(&particle_data, plain_particle_stream))
        processParticle(&particle_data, event_header_data);
}
