#include <stdio.h>
#include <math.h>
#include <sys/types.h>
#include <libgen.h>
#include <errno.h>
#include <stdbool.h>

#include "./globals.h"
#include "./iterator.h"

void initParticleFileStats(ParticleFileStats *s)
{
    s->nRUNH = 0;
    s->nRUNE = 0;
    s->nEVTH = 0;
    s->nEVTE = 0;
    s->nLONG = 0;
    s->nPARTSUB = 0;
    s->n_blocks_total = 0;
}

void readEventHeaderData(EventHeaderData *d, FILE *file)
{
    fread(d->eventbuf, sizeof(float), NWORD, file);
    d->origin[0] = -d->eventbuf[7] / d->eventbuf[9] * (d->eventbuf[6] - observationLevel);
    d->origin[1] = -d->eventbuf[8] / d->eventbuf[9] * (d->eventbuf[6] - observationLevel);
    d->origin[2] = d->eventbuf[6];
    d->tmin = hypotf(hypotf(d->origin[0], d->origin[1]), d->origin[2] - observationLevel) / CSPEED;
    d->zenith = eventbuf[10];
}

void readParticleData(ParticleData *pd, FILE *file)
{
    fread(pd->partbuf, sizeof(float), NPART, file);
    pd->id = (int)pd->partbuf[0] / 1000.0;
    float p = hypotf(pd->partbuf[3], hypotf(pd->partbuf[1], pd->partbuf[2]));
    float mass = pmass[pd->id];
    pd->energy = hypotf(mass, p) - mass;
}

// Generic iterator over CORSIKA output particle file, executing a callback on each particle
// returns success flag
bool iterateParticleFile(
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
        fprintf(stdout, "Opening %s file\n", particle_filename);
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
                readEventHeaderData(event_header_data, fparticle);
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
                for (int iParticleSubblock = 0; iParticleSubblock < NSENTENCE; iParticleSubblock++)
                {
                    stats->nPARTSUB++;
                    readParticleData(&particle_data, fparticle);
                    processParticle(&particle_data, event_header_data);
                }
            }
        }
        fread(&blocklen, sizeof(int), 1, fparticle);
    }
    fclose(fparticle);
    if (verbose)
    {
        printf("read %d blocks\n", stats->n_blocks_total);
        printf(
            "RUNH: %d, EVTH: %d, PARTSUB: %d, LONG: %d, EVTE: %d, RUNE: %d\n",
            stats->nRUNH, stats->nEVTH, stats->nPARTSUB, stats->nLONG, stats->nEVTE, stats->nRUNE);
    }
    return true;
}
