// Splitting CORSIKA output file to several parts for independent dethinning.

// Originally written by BTS (runcorsd-old/corsika_split-th.c)
// Adapted as a C-extension of `tasdmc` Python package by Igor Vaiman

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>

#define NSUBBLOCK 21
#define NSENTENCE 39
#define NPART 8
#define NWORD NPART *NSENTENCE

#define MAX_SPLIT_PARTS 100

int splitThinnedCorsikaOutput(const char* corsikaOutputFilename, int splitParts)
{
	if (splitParts > MAX_SPLIT_PARTS) {
		return EXIT_FAILURE;
	}

	FILE *fin, *fout;
	int i, nRUNE = 0, nRUNH = 0, nEVTH = 0, nEVTE = 0, nLONG = 0, nPART = 0, nPART2 = 0;
	int filenum = 0, nsub;
	float runhbuf[NWORD], runebuf[NWORD], evthbuf[NWORD], evtebuf[NWORD];
	float partbuf[NWORD], zerobuf[NWORD] = {0.};
	int blockLen;
	off_t RB = sizeof(float);
	char blockName[5], bufName[4], outputFiles[MAX_SPLIT_PARTS][256];

	if ((fin = fopen(corsikaOutputFilename, "rb")) == NULL)
	{
		fprintf(stderr, "Cannot open %s file \n", corsikaOutputFilename);
		return EXIT_FAILURE;
	}

	for (i = 0; i < splitParts; i++)  // .p01, .p02, ... .p99
		sprintf(outputFiles[i], "%s.p%2.2d", corsikaOutputFilename, i + 1);

	while (fread(&blockLen, sizeof(int), 1, fin))
	{
		for (i = 0; i < NSUBBLOCK; i++)
		{
			fread(bufName, sizeof(char), 4, fin);
			fseeko(fin, -RB, SEEK_CUR);
			strncpy(blockName, bufName, 4);
			blockName[4] = '\0';
			if (!strcmp("RUNH", blockName))
			{
				fread(runhbuf, sizeof(float), NWORD, fin);
				nRUNH++;
			}
			else if (!strcmp("EVTH", blockName))
			{
				fread(evthbuf, sizeof(float), NWORD, fin);
				nEVTH++;
			}
			else if (!strcmp("LONG", blockName))
			{
				nLONG++;
				fseeko(fin, NWORD * RB, SEEK_CUR);
			}
			else if (!strcmp("EVTE", blockName))
			{
				fread(evtebuf, sizeof(float), NWORD, fin);
				nEVTE++;
			}
			else if (!strcmp("RUNE", blockName))
			{
				fread(runebuf, sizeof(float), NWORD, fin);
				nRUNE++;
			}
			else
			{
				nPART++;
				fseeko(fin, NWORD * RB, SEEK_CUR);
			}
		}
		fread(&blockLen, sizeof(int), 1, fin);
	}
	fclose(fin);

	if ((fin = fopen(corsikaOutputFilename, "rb")) == NULL)
	{
		fprintf(stderr, "Cannot open %s file \n", corsikaOutputFilename);
		return EXIT_FAILURE;
	}
	filenum = 0;
	if ((fout = fopen(outputFiles[filenum], "wb")) == NULL)
	{
		fprintf(stderr, "Cannot open %s file \n", outputFiles[filenum]);
		return EXIT_FAILURE;
	}
	fwrite(&blockLen, sizeof(int), 1, fout);
	fwrite(runhbuf, sizeof(float), NWORD, fout);
	fwrite(evthbuf, sizeof(float), NWORD, fout);

	nsub = 2;
	while (fread(&blockLen, sizeof(int), 1, fin))
	{
		for (i = 0; i < NSUBBLOCK; i++)
		{
			fread(bufName, sizeof(char), 4, fin);
			fseeko(fin, -RB, SEEK_CUR);
			strncpy(blockName, bufName, 4);
			blockName[4] = '\0';
			if (!strcmp("RUNH", blockName))
				fseeko(fin, NWORD * RB, SEEK_CUR);
			else if (!strcmp("EVTH", blockName))
				fseeko(fin, NWORD * RB, SEEK_CUR);
			else if (!strcmp("LONG", blockName))
				fseeko(fin, NWORD * RB, SEEK_CUR);
			else if (!strcmp("EVTE", blockName))
				fseeko(fin, NWORD * RB, SEEK_CUR);
			else if (!strcmp("RUNE", blockName))
				fseeko(fin, NWORD * RB, SEEK_CUR);
			else
			{
				nPART2++;
				fread(partbuf, sizeof(float), NWORD, fin);
				fwrite(partbuf, sizeof(float), NWORD, fout);
				nsub++;
				if (nsub == NSUBBLOCK)
				{
					nsub = 0;
					fwrite(&blockLen, sizeof(int), 1, fout);
					fwrite(&blockLen, sizeof(int), 1, fout);
				}
				if (((nPART2 - 1) * splitParts) / nPART > filenum)
				{
					filenum++;
					fwrite(evtebuf, sizeof(float), NWORD, fout);
					nsub++;
					if (nsub == NSUBBLOCK)
					{
						nsub = 0;
						fwrite(&blockLen, sizeof(int), 1, fout);
						fwrite(&blockLen, sizeof(int), 1, fout);
					}
					fwrite(runebuf, sizeof(float), NWORD, fout);
					nsub++;
					while (nsub < NSUBBLOCK)
					{
						fwrite(zerobuf, sizeof(float), NWORD, fout);
						nsub++;
					}
					nsub = 0;
					fwrite(&blockLen, sizeof(int), 1, fout);
					fclose(fout);
					if ((fout = fopen(outputFiles[filenum], "wb")) == NULL)
					{
						fprintf(stderr, "Cannot open %s file \n",
								outputFiles[filenum]);
						exit(EXIT_FAILURE);
					}
					fwrite(&blockLen, sizeof(int), 1, fout);
					fwrite(runhbuf, sizeof(float), NWORD, fout);
					fwrite(evthbuf, sizeof(float), NWORD, fout);
					nsub = 2;
				}
			}
		}
		fread(&blockLen, sizeof(int), 1, fin);
	}
	fwrite(evtebuf, sizeof(float), NWORD, fout);
	nsub++;
	if (nsub == NSUBBLOCK)
	{
		nsub = 0;
		fwrite(&blockLen, sizeof(int), 1, fout);
		fwrite(&blockLen, sizeof(int), 1, fout);
	}
	fwrite(runebuf, sizeof(float), NWORD, fout);
	nsub++;
	while (nsub < NSUBBLOCK)
	{
		fwrite(zerobuf, sizeof(float), NWORD, fout);
		nsub++;
	}
	nsub = 0;
	fwrite(&blockLen, sizeof(int), 1, fout);
	fclose(fout);
	fclose(fin);

	return EXIT_SUCCESS;
}
