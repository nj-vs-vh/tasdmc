#include <stdio.h>
#include <math.h>
#include <sys/types.h>
#include <libgen.h>
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>

#define MAP_SIDE 16800 // meters
#define TILE_SIDE 6    // meters
#define DISTMAX (MAP_SIDE / 2)
#define NX (MAP_SIDE / TILE_SIDE)
#define NY (MAP_SIDE / TILE_SIDE)

#define SENTINEL_TIME 1e9

#define DT 20               // time bin duration, nsec
#define T_BATCH (DT * NT)   // length of time bins' batch; NT gives a number of time bins in a batch
#define TMAX 1280           // time bins total

#define VEM 2.05            // MeV
#define CSPEED 29.97925     // cm/nsec
#define PI 3.14159265359

static const float pmass[26] = {0., 0., 0.511e-3, .511e-3, 0., 105.7e-3, 105.7e-3, 135.e-3,
                                140.e-3, 140.e-3, 498.e-3, 494.e-3, 494.e-3, 940.e-3, 938.e-3,
                                938.e-3, 498.e-3, 549.e-3, 1116.e-3, 1189.e-3, 1193.e-3,
                                1197.e-3, 1315.e-3, 1321.e-3, 1672e-3, 940.e-3};

static const float observationLevel = 1430.e2; // cm, above sea level

// file IO stuff

#define NSENTENCE 39 // particles in one data sub-block
#define NPART 8      // floats in particle record  <------------------ NOT 7 BUT 8 BECAUSE EACH PARTICLE HAS +1 PARAM
#define NWORD (NPART * NSENTENCE)
#define NSUBBLOCK 21 // data sub-blocks per block
#define TILE_FILE_BLOCK_SIZE 6

bool printZenithAngleFromCorsika(const char *particle_filename)
{
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
    while (fread(&blocklen, sizeof(int), 1, fparticle))
    {
        for (int iSubblock = 0; iSubblock < NSUBBLOCK; iSubblock++)
        {
            fread(block_name_buf, sizeof(char), 4, fparticle);
            fseeko(fparticle, -RB, SEEK_CUR);
            strncpy(block_name, block_name_buf, 4);
            block_name[4] = '\0';
            if (!strcmp("EVTH", block_name))
            {
                float eventbuf[NWORD];
                fread(eventbuf, sizeof(float), NWORD, fparticle);
                printf("%g\n", eventbuf[10]);  // <----------------------------------- printing zenith angle here
                // break;
            }
            else {
                fread(buf, sizeof(float), NWORD, fparticle);
            }
        }
        fread(&blocklen, sizeof(int), 1, fparticle);
    }
    fclose(fparticle);
    return true;
}


int main(int argc, char *argv[]) {
    if (argc != 2)
    {
        printf("Hi\n");
        exit(1);
    }
    const char *particle_file = argv[1];

    printZenithAngleFromCorsika(particle_file);
}
