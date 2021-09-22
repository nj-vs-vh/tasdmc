#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>

#define  NSUBBLOCK 21
#define  NSENTENCE 39
#define  NPART 8
#define  NWORD NPART*NSENTENCE

int main(int argc, char **argv)
{
  FILE *f, *fout;
  int i, nRUNE=0, nRUNH=0, nEVTH=0, nEVTE=0, nLONG=0, nPART=0, nPART2=0;
  int nFILE=1, filenum=0, nsub;
  float runhbuf[NWORD], runebuf[NWORD], evthbuf[NWORD], evtebuf[NWORD];
  float partbuf[NWORD], zerobuf[NWORD] = {0.};
  int blockLen;
  off_t RB=sizeof(float);
  char blockName[5], bufName[4], outFile[100][256];

  if (( f = fopen(argv[1], "rb")) == NULL )
    {
      fprintf(stderr,"Cannot open %s file \n", argv[1]);
      exit(EXIT_FAILURE);
    }
  sscanf(argv[2], "%d", &nFILE);
  for ( i = 0; i < nFILE; i++ )
    sprintf(outFile[i], "%s.p%2.2d", argv[1], i+1);
  while( fread ( &blockLen, sizeof(int), 1, f))
    {
      for (i = 0; i < NSUBBLOCK; i++)
	{
      	  fread(bufName, sizeof(char), 4, f);
	  fseeko(f, -RB, SEEK_CUR);
	  strncpy(blockName, bufName, 4);
	  blockName[4] = '\0';
	  if (!strcmp("RUNH", blockName)) 
	    {
	      fread(runhbuf, sizeof(float), NWORD, f);
	      nRUNH++;
	    }
	  else if (!strcmp("EVTH", blockName)) 
	    {
	      fread(evthbuf, sizeof(float), NWORD, f);
	      nEVTH++;
	    }
	  else if (!strcmp("LONG", blockName)) 
	    {
	      nLONG++;
	      fseeko(f, NWORD*RB, SEEK_CUR);
	    }
          else if (!strcmp("EVTE", blockName)) 
	    {
	      fread(evtebuf, sizeof(float), NWORD, f);
	      nEVTE++;
	    }
	  else if (!strcmp("RUNE", blockName)) 
	    {
	      fread(runebuf, sizeof(float), NWORD, f);
	      nRUNE++;
	    }
	  else 
	    {
	      nPART++;
	      fseeko(f, NWORD*RB, SEEK_CUR);
	    }
	}	  
      fread(&blockLen, sizeof(int), 1, f);
    }
  fclose(f);
  if (( f = fopen(argv[1], "rb")) == NULL )
    {
      fprintf(stderr,"Cannot open %s file \n", argv[1]);
      exit(EXIT_FAILURE);
    }
  filenum = 0;
  if (( fout = fopen(outFile[filenum], "wb")) == NULL )
    {
      fprintf(stderr,"Cannot open %s file \n", outFile[filenum]);
      exit(EXIT_FAILURE);
    }
  fwrite(&blockLen, sizeof(int), 1, fout); 
  fwrite(runhbuf, sizeof(float), NWORD, fout);
  fwrite(evthbuf, sizeof(float), NWORD, fout);
  nsub=2;
  while( fread ( &blockLen, sizeof(int), 1, f))
    {
      for (i = 0; i < NSUBBLOCK; i++)
	{
      	  fread(bufName, sizeof(char), 4, f);
	  fseeko(f, -RB, SEEK_CUR);
	  strncpy(blockName, bufName, 4);
	  blockName[4] = '\0';
	  if (!strcmp("RUNH", blockName)) fseeko(f, NWORD*RB, SEEK_CUR); 
	  else if (!strcmp("EVTH", blockName)) fseeko(f, NWORD*RB, SEEK_CUR);
	  else if (!strcmp("LONG", blockName)) fseeko(f, NWORD*RB, SEEK_CUR);
          else if (!strcmp("EVTE", blockName)) fseeko(f, NWORD*RB, SEEK_CUR);
	  else if (!strcmp("RUNE", blockName)) fseeko(f, NWORD*RB, SEEK_CUR);
	  else 
	    {
	      nPART2++;
	      fread (partbuf, sizeof(float), NWORD, f);
	      fwrite(partbuf, sizeof(float), NWORD, fout);
	      nsub++;
	      if (nsub == NSUBBLOCK) 
		{
		  nsub=0;
		  fwrite(&blockLen, sizeof(int), 1, fout); 
		  fwrite(&blockLen, sizeof(int), 1, fout); 
		}
	      if (((nPART2-1)*nFILE)/nPART > filenum)
		{
		  filenum++;
		  fwrite(evtebuf, sizeof(float), NWORD, fout);
		  nsub++;
		  if (nsub == NSUBBLOCK) 
		    {
		      nsub=0;
		      fwrite(&blockLen, sizeof(int), 1, fout); 
		      fwrite(&blockLen, sizeof(int), 1, fout); 
		    }
		  fwrite(runebuf, sizeof(float), NWORD, fout);
		  nsub++;
		  while ( nsub < NSUBBLOCK )
		    {
		      fwrite(zerobuf, sizeof(float), NWORD, fout);
		      nsub++;
		    }
		  nsub=0;
		  fwrite(&blockLen, sizeof(int), 1, fout); 
		  fclose(fout);
		  if (( fout = fopen(outFile[filenum], "wb")) == NULL )
		    {
		      fprintf(stderr,"Cannot open %s file \n", 
			      outFile[filenum]);
		      exit(EXIT_FAILURE);
		    }
		  fwrite(&blockLen, sizeof(int), 1, fout); 
		  fwrite(runhbuf, sizeof(float), NWORD, fout);
		  fwrite(evthbuf, sizeof(float), NWORD, fout);
		  nsub=2;
		}
	    }
	}	  
      fread(&blockLen, sizeof(int), 1, f);
    }
  fwrite(evtebuf, sizeof(float), NWORD, fout);
  nsub++;
  if (nsub == NSUBBLOCK) 
    {
      nsub=0;
      fwrite(&blockLen, sizeof(int), 1, fout); 
      fwrite(&blockLen, sizeof(int), 1, fout); 
    }
  fwrite(runebuf, sizeof(float), NWORD, fout);
  nsub++;
  while ( nsub < NSUBBLOCK )
    {
      fwrite(zerobuf, sizeof(float), NWORD, fout);
      nsub++;
    }
  nsub=0;
  fwrite(&blockLen, sizeof(int), 1, fout); 
  fclose(fout);
  fclose(f);
  return 0;
}
