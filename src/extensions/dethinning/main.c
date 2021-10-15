// Dethinning procedure on thinned CORSIKA output, i.e. replacing N-weighted CORSIKA particle with
// N particles spread across observation plane

// Originally written by BTS (runcorsd-old/deweight2.c)
// Adapted as a C-extension of `tasdmc` Python package by Igor Vaiman

#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>

#include "./constants.h"
#include "./atmosphere.h"
#include "./corsika_weights.h"

// in-memory buffering can help speed up dethinning by first accumulating data in RAM
// and only then writing it to file with an expensive syscall
// set INMENORY_BUFFER_SIZE to some reasonably large constant
// TODO: determine INMENORY_BUFFER_SIZE from TASDMC_MEMORY_PER_PROCESS_GB dynamically
#define INMEMORY_BUFFERING  // uncomment to turn buffering on
#define INPUTBUFFER_SIZE 1024 * 128 // bytes
#define OUTPUTBUFFER_SIZE 1024 * 512 // bytes

#include "./globals.h"
// defining global variables
float coszenith;
float origin[3], normorig[3];
float Z0;

int dethinning(
	const char *particleFilename,
	const char *longtitudeFilename,
	const char *outputFilename,
	bool verbose)
{
	FILE *fin, *fout, *flong;
	char longtitudeFileLine[1024];

	// CORSIKA reading stuff
	int i, j, m, nRUNH = 0, nEVTH = 0, nLONG = 0, nEVTE = 0, nRUNE = 0, nBlock = 0;
	int nPARTSUB = 0, sblockcount = 0, partcount = 0, wcount;
	int blockLen, blockLen2 = 4 * NPART2 * NSENTENCE * NSUBBLOCK;
	char blockName[5], bufName[4];
	float buf[NWORD], buf2[NWORD2], buf3[NPART], buf4[NPART2], R0[3], d1[3];
	float R1[3], energy, dist, R, pln1[3], pln2[3], blurscale;
	float DISTMIN1, DISTMIN2, enlog, ptot, latdist, mo, toffset = 0;
	float otmp[3], height_long = 1.e12, npart[9], x0, secnew, enew;
	off_t RB = sizeof(float);

	#ifdef INMEMORY_BUFFERING
	char outputBuffer[OUTPUTBUFFER_SIZE];
	char inputBuffer[INPUTBUFFER_SIZE];
	#endif

	//Open input file
	if ((fin = fopen(particleFilename, "rb")) == NULL)
	{
		if (verbose)
			fprintf(stderr, "Cannot open %s file \n", particleFilename);
		return EXIT_FAILURE;
	}
	#ifdef INMEMORY_BUFFERING
	setvbuf(fin, inputBuffer, _IOFBF, INPUTBUFFER_SIZE);
	#endif

	//Open longitudinal development file (optional)
	if ((flong = fopen(longtitudeFilename, "r")) == NULL)
	{
		if (verbose)
			fprintf(stdout, "Not using longitudinal profile for height determination\n");
	}
	else
	{
		//Process longitudinal development file to check for preshowering
		fgets(longtitudeFileLine, 1023, flong);
		fgets(longtitudeFileLine, 1023, flong);
		fgets(longtitudeFileLine, 1023, flong);
		sscanf(longtitudeFileLine, "%f %f %f %f %f %f %f %f %f %f\n", &x0, &npart[0],
			   &npart[1], &npart[2], &npart[3], &npart[4], &npart[5],
			   &npart[6], &npart[7], &npart[8]);
		if (npart[0] + npart[1] + npart[2] + npart[3] + npart[4] + npart[5] + npart[7] > 1.)
		{
			x0 = 0.;
			height_long = 1.e12;
			fclose(flong);
		}
		else
		{
			while (fgets(longtitudeFileLine, 1023, flong))
			{
				if (sscanf(longtitudeFileLine, "%f %f %f %f %f %f %f %f %f %f\n", &x0,
						   &npart[0], &npart[1], &npart[2], &npart[3],
						   &npart[4], &npart[5],
						   &npart[6], &npart[7], &npart[8]) != 10)
				{
					if (verbose)
						fprintf(stderr, "Primary particle is non-interacting\n");
					return EXIT_FAILURE;
				}
				else
				{
					if (npart[0] + npart[1] + npart[2] + npart[3] + npart[4] + npart[5] + npart[7] > 1.)
					{
						height_long = mo2h(x0, ATMOS_MODEL);
						if (verbose)
							fprintf(stdout, "x0=%f; H (from .long file)=%f\n", x0, height_long);
						fclose(flong);
						continue;
					}
				}
			}
		}
	}

	// Check output file for writeability
	if ((fout = fopen(outputFilename, "wb")) == NULL)
	{
		if (verbose)
			fprintf(stderr, "Cannot open %s file \n", outputFilename);
		return EXIT_FAILURE;
	}

	#ifdef INMEMORY_BUFFERING
	setvbuf(fout, outputBuffer, _IOFBF, OUTPUTBUFFER_SIZE);
	#endif

	fwrite(&blockLen2, sizeof(int), 1, fout);

	//Read/write CORSIKA input and dethinned output

	while (fread(&blockLen, sizeof(int), 1, fin))
	{
		nBlock++;
		for (i = 0; i < NSUBBLOCK; i++)
		{
			fread(bufName, sizeof(char), 4, fin);
			fseeko(fin, -RB, SEEK_CUR);
			strncpy(blockName, bufName, 4);
			blockName[4] = '\0';

			//Read/write run header

			if (!strcmp("RUNH", blockName))
			{
				nRUNH++;
				fread(buf, sizeof(float), NWORD, fin);
				for (m = 0; m < NWORD2; m++)
					buf2[m] = buf[m];
				fwrite(buf2, sizeof(float), NWORD2, fout);
				sblockcount++;
				if (sblockcount == NSUBBLOCK)
				{
					sblockcount = 0;
					fwrite(&blockLen2, sizeof(int), 1, fout);
					fwrite(&blockLen2, sizeof(int), 1, fout);
				}
			}

			//Read/write/process event header

			else if (!strcmp("EVTH", blockName))
			{
				nEVTH++;
				fread(buf, sizeof(float), NWORD, fin);
				for (m = 0; m < NWORD2; m++)
					buf2[m] = buf[m];
				coszenith = cosf(buf[10]); // TODO: pass this as a param where it is needed

				//Calculate event trajectory

				R0[0] = buf[7] / buf[3];
				R0[1] = buf[8] / buf[3];
				R0[2] = -buf[9] / buf[3];
				Z0 = buf[47]; // TODO: pass this as a param where it is needed

				enlog = log10f(buf[3]) - 10.;

				//Calculate size of event annuli

				if (enlog < 0.)
					DISTMIN2 = DISTMED + DISTA * enlog;
				else
					DISTMIN2 = DISTMED + DISTB * enlog;
				DISTMIN1 = DISTMIN2 - 200.;
				if (DISTMIN1 < 100.)
					DISTMIN1 = 100.;
				if (DISTMIN2 < 300.)
					DISTMIN2 = 300.;
				normalizef(R0, R0);

				//Calculate point of first interaction

				origin[0] = -buf[7] / buf[9] * (buf[6] - Z0);
				origin[1] = -buf[8] / buf[9] * (buf[6] - Z0);
				origin[2] = buf[6];

				//Account for preshowering

				if (height_long < buf[6])
				{
					otmp[0] = -buf[7] / buf[9] * (height_long - Z0);
					otmp[1] = -buf[8] / buf[9] * (height_long - Z0);
					otmp[2] = height_long;
					toffset = hypotf(
								  (otmp[2] - origin[2]), hypotf((otmp[1] - origin[1]), (otmp[0] - origin[0]))) /
							  CSPEED;
					origin[0] = otmp[0];
					origin[1] = otmp[1];
					origin[2] = otmp[2];
					buf2[6] = height_long;
				}
				fwrite(buf2, sizeof(float), NWORD2, fout);
				if (verbose)
				{
					fprintf(stdout, "Primary Event Direction: %g\t%g\t%g\n",
							R0[0], R0[1], R0[2]);
					fprintf(stdout, "Origin: %g\t%g\t%g\t%g\n",
							origin[0], origin[1], origin[2], -toffset);
				}
				sblockcount++;
				if (sblockcount == NSUBBLOCK)
				{
					sblockcount = 0;
					fwrite(&blockLen2, sizeof(int), 1, fout);
					fwrite(&blockLen2, sizeof(int), 1, fout);
				}
			}

			//Read/write longitudinal bank

			else if (!strcmp("LONG", blockName))
			{
				nLONG++;
				if (partcount != 0)
				{
					for (m = 0; m < NPART2; m++)
						buf4[m] = 0.;
					for (m = 0; m < NSENTENCE - partcount; m++)
						fwrite(buf4, sizeof(float), NPART2, fout);
					partcount = 0;
					sblockcount++;
					if (sblockcount == NSUBBLOCK)
					{
						sblockcount = 0;
						fwrite(&blockLen2, sizeof(int), 1, fout);
						fwrite(&blockLen2, sizeof(int), 1, fout);
					}
				}
				fread(buf, sizeof(float), NWORD, fin);
				for (m = 0; m < NWORD2; m++)
					buf2[m] = buf[m];
				fwrite(buf2, sizeof(float), NWORD2, fout);
				sblockcount++;
				if (sblockcount == NSUBBLOCK)
				{
					sblockcount = 0;
					fwrite(&blockLen2, sizeof(int), 1, fout);
					fwrite(&blockLen2, sizeof(int), 1, fout);
				}
			}

			//Read/write event footer

			else if (!strcmp("EVTE", blockName))
			{
				if (partcount != 0)
				{
					for (m = 0; m < NPART2; m++)
						buf4[m] = 0.;
					for (m = 0; m < NSENTENCE - partcount; m++)
						fwrite(buf4, sizeof(float), NPART2, fout);
					partcount = 0;
					sblockcount++;
					if (sblockcount == NSUBBLOCK)
					{
						sblockcount = 0;
						fwrite(&blockLen2, sizeof(int), 1, fout);
						fwrite(&blockLen2, sizeof(int), 1, fout);
					}
				}
				nEVTE++;
				fread(buf, sizeof(float), NWORD, fin);
				for (m = 0; m < NWORD2; m++)
					buf2[m] = buf[m];
				fwrite(buf2, sizeof(float), NWORD2, fout);
				sblockcount++;
				if (sblockcount == NSUBBLOCK)
				{
					sblockcount = 0;
					fwrite(&blockLen2, sizeof(int), 1, fout);
					fwrite(&blockLen2, sizeof(int), 1, fout);
				}
			}

			//Read/write run footer

			else if (!strcmp("RUNE", blockName))
			{
				if (partcount != 0)
				{
					for (m = 0; m < NPART2; m++)
						buf4[m] = 0.;
					for (m = 0; m < NSENTENCE - partcount; m++)
						fwrite(buf4, sizeof(float), NPART2, fout);
					partcount = 0;
					sblockcount++;
					if (sblockcount == NSUBBLOCK)
					{
						sblockcount = 0;
						fwrite(&blockLen2, sizeof(int), 1, fout);
						fwrite(&blockLen2, sizeof(int), 1, fout);
					}
				}
				nRUNE++;
				fread(buf, sizeof(float), NWORD, fin);
				for (m = 0; m < NWORD2; m++)
					buf2[m] = buf[m];
				fwrite(buf2, sizeof(float), NWORD2, fout);
				sblockcount++;
				if (sblockcount != NSUBBLOCK)
				{
					for (m = 0; m < NWORD2; m++)
						buf2[m] = 0.;
					for (m = 0; m < NSUBBLOCK - sblockcount; m++)
						fwrite(buf2, sizeof(float), NWORD2, fout);
				}
				fwrite(&blockLen2, sizeof(int), 1, fout);
				fclose(fin);
				fclose(fout);
				if (verbose)
				{
					fprintf(stdout, "read %d blocks\n", nBlock);
					fprintf(stdout, "RUNH: %d, EVTH: %d, PARTSUB: %d, LONG: %d, EVTE: %d, RUNE: %d\n",
							nRUNH, nEVTH, nPARTSUB, nLONG, nEVTE, nRUNE);
				}
				return EXIT_SUCCESS;
			}

			//Read/write/dethin particles

			else
			{
				for (j = 0; j < NSENTENCE; j++)
				{
					nPARTSUB++;
					fread(buf3, sizeof(float), NPART, fin);
					buf3[6] -= toffset;
					for (m = 0; m < NPART2; m++)
						buf4[m] = buf3[m];
					if (hypotf(buf4[4], buf4[5]) / 100. > DISTMIN2 &&
						hypotf(buf4[4], buf4[5]) / 100. < DISTMAX)
					{
						ptot = hypotf(buf4[1], hypotf(buf4[2], buf4[3]));
						secnew = ptot / buf4[3];

						//Calulate kinetic energy

						enew = hypotf(pmass[(int)(buf4[0] / 1000.)], ptot) -
							   pmass[(int)(buf4[0] / 1000.)];

						//Pass through original trajectory of weighted particle

						fwrite(buf4, sizeof(float), NPART2, fout);
						partcount++;
						if (partcount == NSENTENCE)
						{
							partcount = 0;
							sblockcount++;
							if (sblockcount == NSUBBLOCK)
							{
								sblockcount = 0;
								fwrite(&blockLen2, sizeof(int), 1, fout);
								fwrite(&blockLen2, sizeof(int), 1, fout);
							}
						}
					}

					//check if event is outside inner annulus

					if (hypotf(buf4[4], buf4[5]) / 100. > DISTMIN1 &&
						buf4[0] >= 1000. && buf4[0] < 26000.)
					{
						ptot = hypotf(buf4[1], hypotf(buf4[2], buf4[3]));
						enew = hypotf(pmass[(int)(buf4[0] / 1000.)], ptot) -
							   pmass[(int)(buf4[0] / 1000.)];
						if (buf3[7] > 1.)
						{
							if ((float)drand48() > (buf3[7] - floorf(buf3[7])))
								wcount = (int)buf3[7] - 1;
							else
								wcount = (int)buf3[7];
							weightPrep_t(buf3, R0, d1, R1, &energy, &dist, &R,
										 pln1, pln2, &latdist, &mo);
							if (buf3[0] > 5000.)
								blurscale = 1.0;
							else
								blurscale = 3.0;
							for (m = 0; m < wcount; m++)
							{
								weightThrow(d1, R1, pln1, pln2, R, energy, dist,
											buf3[6],
											blurscale / RADDEG * latdist / 1.e5,
											buf4,
											(int)(buf4[0] / 1000.),
											mo);
								if (hypotf(buf4[4], buf4[5]) / 100. > DISTMIN2 &&
									hypotf(buf4[4], buf4[5]) / 100. < DISTMAX)
								{
									secnew = ptot / buf4[3];
									fwrite(buf4, sizeof(float), NPART2, fout);
									partcount++;
									if (partcount == NSENTENCE)
									{
										partcount = 0;
										sblockcount++;
										if (sblockcount == NSUBBLOCK)
										{
											sblockcount = 0;
											fwrite(&blockLen2, sizeof(int), 1,
												   fout);
											fwrite(&blockLen2, sizeof(int), 1,
												   fout);
										}
									}
								}
							}
						}
					}
				}
			}
		}
		fread(&blockLen, sizeof(int), 1, fin);
	}

	if (verbose)
	{
		fprintf(stderr, "CORSIKA EVENT DID NOT END WITH RUNE BANK\n");
		fprintf(stderr, "read %d blocks\n", nBlock);
		fprintf(stderr, "RUNH: %d, EVTH: %d, PARTSUB: %d, LONG: %d, EVTE: %d, RUNE: %d\n",
				nRUNH, nEVTH, nPARTSUB, nLONG, nEVTE, nRUNE);
	}
	return EXIT_FAILURE;
}
