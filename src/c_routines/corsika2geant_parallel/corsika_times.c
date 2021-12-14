#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>

#include "./globals.h"
#include "./corsika_times.h"
#include "./iterator.h"

double corsika_times(const char *particleFilesList)
{
    const off_t RB = sizeof(float);

    int i, j, m, n;

    int blockLen;
    int nBlockTotal, eventCount = 0;
    float energy, buf[NWORD], particleBuf[NPART];
    double count = 0.;
    FILE *fparticle, *flist;
    int nRUNH, nEVTH, nLONG, nEVTE, nRUNE;
    int nPARTSUB, outliersCount = 0;
    char blockName[5], blockNameBuf[4], particleFilename[256];
    tmin = 1.e9;
    for (i = 0; i < NX; i++)
    {
        for (j = 0; j < NY; j++)
        {
            time1[i][j] = 1.e9;
        }
    }

    // iterateParticleFile()

    fprintf(stdout, "Opening %s filelist\n", particleFilesList);
    if ((flist = fopen(particleFilesList, "r")) == NULL)
    {
        fprintf(stderr, "Cannot open %s file: %s\n", particleFilesList, strerror(errno));
        return EXIT_FAILURE_DOUBLE;
    }
    nRUNH = nEVTH = nLONG = nEVTE = nRUNE = 0;
    nPARTSUB = 0;
    nBlockTotal = 0;
    while (fscanf(flist, "%s\n", particleFilename) != EOF)
    {
        if ((fparticle = fopen(particleFilename, "rb")) == NULL)
        {
            fprintf(stderr, "Cannot open %s file \n", particleFilename);
            return EXIT_FAILURE_DOUBLE;
        }
        fprintf(stdout, "Opening %s file\n", particleFilename);
        while (fread(&blockLen, sizeof(int), 1, fparticle))
        {
            nBlockTotal++;
            for (i = 0; i < NSUBBLOCK; i++)
            {
                fread(blockNameBuf, sizeof(char), 4, fparticle);
                fseeko(fparticle, -RB, SEEK_CUR);
                strncpy(blockName, blockNameBuf, 4);
                blockName[4] = '\0';
                if (!strcmp("RUNH", blockName))
                {
                    nRUNH++;
                    fread(buf, sizeof(float), NWORD, fparticle);
                }
                else if (!strcmp("EVTH", blockName))
                {
                    if (nEVTH > eventCount)
                    {
                        fprintf(stderr, "There is more than one CORSIKA event in %s, only reading the first event\n", particleFilename);
                        return count;
                    }
                    nEVTH++;
                    fread(eventbuf, sizeof(float), NWORD, fparticle);
                    origin[0] = -eventbuf[7] / eventbuf[9] * (eventbuf[6] - observationLevel);
                    origin[1] = -eventbuf[8] / eventbuf[9] * (eventbuf[6] - observationLevel);
                    origin[2] = eventbuf[6];
                    tmin = hypotf(hypotf(origin[0], origin[1]), origin[2] - observationLevel) / CSPEED;
                    zenith = eventbuf[10];
                }
                else if (!strcmp("LONG", blockName))
                {
                    fread(buf, sizeof(float), NWORD, fparticle);
                    nLONG++;
                }
                else if (!strcmp("EVTE", blockName))
                {
                    nEVTE++;
                    fread(buf, sizeof(float), NWORD, fparticle);
                }
                else if (!strcmp("RUNE", blockName))
                {
                    nRUNE++;
                    fread(buf, sizeof(float), NWORD, fparticle);
                }
                else
                {
                    for (j = 0; j < 39; j++) // WTF is 39?
                    {
                        nPARTSUB++;
                        fread(particleBuf, sizeof(float), NPART, fparticle);
                        if (fabsf(particleBuf[4]) < (float)(100 * DISTMAX) &&
                            fabsf(particleBuf[5]) < (float)(100 * DISTMAX) &&
                            particleBuf[6] > 1.e4)
                        {
                            int particleID = (int)(particleBuf[0] / 1000.);
                            energy = hypotf(particleBuf[3], hypotf(particleBuf[1], particleBuf[2]));
                            energy = hypotf(pmass[particleID], energy) - pmass[particleID];
                            m = (int)((particleBuf[4] + (float)(100 * DISTMAX)) / 600.);
                            n = (int)((particleBuf[5] + (float)(100 * DISTMAX)) / 600.);
                            if (particleID >= 1 && particleID < 26 && energy > emin / 1.e6)
                            {
                                count++;
                                if (particleBuf[6] < time1[m][n])
                                {
                                    if (particleBuf[6] < sqrtf(powf(origin[0] - particleBuf[4], 2.) +
                                                        powf(origin[1] - particleBuf[5], 2.) +
                                                        powf(origin[2] - observationLevel, 2.)) /
                                                      CSPEED)
                                    {
                                        outliersCount++;
                                    }
                                    else
                                    {
                                        time1[m][n] = particleBuf[6];
                                    }
                                }
                            }
                        }
                    }
                }
            }
            fread(&blockLen, sizeof(int), 1, fparticle);
        }
        fclose(fparticle);
        eventCount++;
    }

    fclose(flist);
    printf("Number of Outliers: %d\nTime of Core Impact: %g", outliersCount, tmin);
    printf("read %d blocks\n", nBlockTotal);
    printf("RUNH: %d, EVTH: %d, PARTSUB: %d, INT: %d, EVTE: %d, RUNE: %d\n", nRUNH, nEVTH, nPARTSUB, nLONG, nEVTE, nRUNE);
    fill_time();
    for (i = 0; i < NX; i++)
        for (j = 0; j < NY; j++)
            time1[i][j] = tmin + (float)DT * floorf((time1[i][j] - tmin) / (float)DT);
    return count;
}

void fill_time()
{
    int m = NX / 2;
    int n, m1, m2, n1, n2;
    float x, y, x2, y2;
    while (time1[m][NY / 2] == 1.e9)
        m++;
    filldist = (float)m * 6.0 - (float)DISTMAX + 5.;
    printf("Annulus Diameter: %g\n", filldist);
    dm = m - NX / 2 + 5;
    dn = dm;
    for (m = NX / 2 - dm; m < NX / 2 + dm; m++)
        for (n = NY / 2 - dn; n < NY / 2 + dn; n++)
        {
            x = (float)m * 6.0 - (float)DISTMAX + 3.0;
            y = (float)n * 6.0 - (float)DISTMAX + 3.0;
            if (hypotf(x, y) < filldist)
            {
                x2 = x / hypotf(x, y) * (filldist + 7.5);
                y2 = y / hypotf(x, y) * (filldist + 7.5);
                m1 = (int)((x2 + (float)DISTMAX) / 6.);
                n1 = (int)((y2 + (float)DISTMAX) / 6.);
                m2 = (int)((-x2 + (float)DISTMAX) / 6.);
                n2 = (int)((-y2 + (float)DISTMAX) / 6.);
                time1[m][n] = (time1[m1][n1] + time1[m2][n2]) / 2.;
                time1[m][n] += (time1[m1][n1] - time1[m2][n2]) *
                               hypotf(x, y) / (filldist + 7.5) / 2.0;
            }
        }
}
