// Based on runcorsd-old/corsika2geant.c

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>

#include "./corsika_times.h"
#include "./corsika_vem_init.h"
#include "./corsika_vem.h"
#include "./eloss_sdgeant.h"

#include "./globals.h"
// defining global variables
float eventbuf[NWORD];
float origin[3], zenith;
float time1[NX][NY], tmin, filldist, emin;
int dm, dn;
unsigned short vemcount[NX][NY][NT][2];
unsigned short pz[NX][NY][NT];

int main(int argc, char *argv[])
{
    // command line arguments parsing
    if (argc != 4)
    {
        fprintf(
            stderr,
            "corsika2geant accepts exactly 3 command-line arguments:\n"
            "\tlist of CORSIKA particle file paths to process\n"
            "\tsdgeant.dst file path\n"
            "\toutput file path\n");
        exit(EXIT_FAILURE);
    }
    const char *particleFilesListingFile = argv[1];
    const char *geantFile = argv[2];
    const char *outputFile = argv[3];

    FILE *fout;

    char tmpFile[1000][256];
    unsigned short buf[6];
    int i, j, m, n, tcount;
    double count, count2;
    // srand48(314159265);
    tcount = 0;
    count = count2 = 0.;

    // ??????????????????????????????????????????????????????????????????
    // what does it mean
    // geant file name should also specify minimum energy?
    // ??????????????????????????????????????????????????????????????????

    // if (geantFile != NULL)
    //     sscanf(geantFile, "%f", &emin);
    // else
    //     emin = 0.;

    // let's just ignore that and hope nothing breaks
    emin = 0.;

    printf("Energy threshold: %f keV\n", emin);
    fflush(stdout);
    strcpy(tmpFile[0], particleFilesListingFile);

    if (load_elosses(geantFile) == -1)
    {
        fprintf(stderr, "Cannot open %s file\n", geantFile);
        exit(EXIT_FAILURE);
    }
    count = corsika_times(particleFilesListingFile);
    if (count == EXIT_FAILURE_DOUBLE)
    {
        fprintf(stderr, "corsika_times(%s) function failed", particleFilesListingFile);
        exit(EXIT_FAILURE);
    }

    fout = fopen(outputFile, "w");
    fwrite(eventbuf, sizeof(float), NWORD, fout);
    printf("%g:%g\t %g Percent\n", count2, count, count2 / count * 100.);
    fflush(stdout);
    sprintf(tmpFile[1], "%s.tmp%3.3d", outputFile, 1);
    count2 += corsika_vem_init(particleFilesListingFile, tmpFile[1], tcount);
    if (count2 == EXIT_FAILURE_DOUBLE)
    {
        fprintf(stderr, "corsika_vem_init(%s, %s, %d) function failed", particleFilesListingFile, tmpFile[1], tcount);
        exit(EXIT_FAILURE);
    }

    printf("%g:%g\t %g Percent\n", count2, count, count2 / count * 100.);
    fflush(stdout);
    for (m = 0; m < NX; m++)
    {
        for (n = 0; n < NY; n++)
        {
            if (time1[m][n] != 1.e9)
            {
                buf[0] = (unsigned short)m;
                buf[1] = (unsigned short)n;
                for (i = 0; i < NT; i++)
                {
                    if (vemcount[m][n][i][0] > 0. ||
                        vemcount[m][n][i][1] > 0.)
                    {
                        buf[2] = vemcount[m][n][i][0];
                        buf[3] = vemcount[m][n][i][1];
                        buf[4] = (unsigned short)((time1[m][n] +
                                                   (float)(tcount * DT * NT) +
                                                   (float)(i * DT) - tmin) /
                                                  DT);
                        buf[5] = pz[m][n][i];
                        if (buf[5] == 0 || 2 * buf[5] > buf[2] + buf[3])
                            buf[5] = (unsigned short)(cosf(zenith) * (float)(buf[2] + buf[3]) / 2.);
                        fwrite(buf, sizeof(short), 6, fout);
                    }
                }
            }
        }
    }
    tcount++;
    for (j = 1; j < (int)ceilf((float)TMAX / (float)NT); j++)
    {
        sprintf(tmpFile[j + 1], "%s.tmp%3.3d", outputFile, j + 1);
        count2 += corsika_vem(tmpFile[j], tmpFile[j + 1], tcount);
        if (count2 == EXIT_FAILURE_DOUBLE)
        {
            fprintf(stderr, "corsika_vem(%s, %s, %d) function failed", tmpFile[j], tmpFile[j + 1], tcount);
            exit(EXIT_FAILURE);
        }

        printf("%g:%g\t %g Percent\n", count2, count, count2 / count * 100.);
        fflush(stdout);
        for (m = 0; m < NX; m++)
        {
            for (n = 0; n < NY; n++)
            {
                if (time1[m][n] != 1.e9)
                {
                    buf[0] = (unsigned short)m;
                    buf[1] = (unsigned short)n;
                    for (i = 0; i < NT; i++)
                    {
                        if (vemcount[m][n][i][0] > 0. ||
                            vemcount[m][n][i][1] > 0.)
                        {
                            buf[2] = vemcount[m][n][i][0];
                            buf[3] = vemcount[m][n][i][1];
                            buf[4] = (unsigned short)((time1[m][n] +
                                                       (float)(tcount * DT * NT) +
                                                       (float)(i * DT) - tmin) /
                                                      DT);
                            buf[5] = pz[m][n][i];
                            if (buf[5] == 0 || 2 * buf[5] > buf[2] + buf[3])
                                buf[5] = (unsigned short)(cosf(zenith) *
                                                          (float)(buf[2] + buf[3]) / 2.);
                            fwrite(buf, sizeof(short), 6, fout);
                        }
                    }
                }
            }
        }
        tcount++;
    }
    fclose(fout);
    fprintf(stdout, "OK");
    exit(EXIT_SUCCESS);
}
