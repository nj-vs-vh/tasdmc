#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>

#include "corsika2geant.h"
#include "eloss_sdgeant.h"

void gauss(double pair[]);


double corsika_vem(char *filename, char *tmpfile, int tcount)
{
  int i, j, k, m, n;
  FILE *f, *fout;
  int nRUNH=0, nEVTH=0, nLONG=0, nEVTE=0, nRUNE=0;
  int nPARTSUB=0, sblockcount=0, partcount=0;
  int blockLen;
  float buf3[NPART];
  float energy, sectheta, buf[NWORD];
  double count2=0., vem_tmp[2], gp[2];
  char blockName[5], bufName[4];
  off_t RB=sizeof(float);
  for (i = 0; i < NX; i++ )
    {
      for (j = 0; j < NY; j++)
	{
	  for (k = 0; k < NT; k++)
	    {
	      vemcount[i][j][k][0] = 0;
	      vemcount[i][j][k][1] = 0;
	      pz[i][j][k] = 0;
	    }
	}
    }
  if (( f = fopen(filename, "r")) == NULL)
    {
      fprintf(stderr,"Cannot open %s file: %s\n", filename, strerror(errno));
      exit(EXIT_FAILURE);
    }
  if (( fout = fopen(tmpfile, "w")) == NULL)
    {
      fprintf(stderr,"Cannot open %s file: %s\n", tmpfile, strerror(errno));
      exit(EXIT_FAILURE);
    }
  fwrite(&blockLen, sizeof(int), 1, fout); 
  while (fread(&blockLen, sizeof(int), 1, f))
    {
      for (i = 0; i < NSUBBLOCK; i++)
	{
          fread(bufName, sizeof(char), 4, f);
          fseeko(f, -RB, SEEK_CUR);
          strncpy(blockName, bufName, 4);
          blockName[4] = '\0';
	  if (!strcmp("RUNH", blockName))
	    {
	      nRUNH++;
	      fread(buf, sizeof(float), NWORD, f);
	      fwrite(buf, sizeof(float), NWORD, fout);
	      sblockcount++;
	      if (sblockcount == NSUBBLOCK)
		{
		  sblockcount = 0;
		  fwrite(&blockLen, sizeof(int), 1, fout);
		  fwrite(&blockLen, sizeof(int), 1, fout);
		}
	    }
	  else if (!strcmp("EVTH", blockName))
	    {
	      nEVTH++;
	      fread(buf, sizeof(float), NWORD, f);
	      fwrite(buf, sizeof(float), NWORD, fout);
	      sblockcount++;
	      if (sblockcount == NSUBBLOCK)
		{
		  sblockcount = 0;
		  fwrite(&blockLen, sizeof(int), 1, fout);
		  fwrite(&blockLen, sizeof(int), 1, fout);
		}
	    }	      
	  else if (!strcmp("LONG", blockName))
	    {
	      nLONG++;
	      if ( partcount != 0 )
		{
		  for ( m = 0; m < NPART; m++)
		    buf3[m] = 0.;
		  for (m = 0; m < NSENTENCE - partcount; m++)
		    fwrite(buf3, sizeof(float), NPART, fout);
		  partcount = 0;
		  sblockcount++;
		  if ( sblockcount == NSUBBLOCK )
		    {
		      sblockcount = 0;
		      fwrite(&blockLen, sizeof(int), 1, fout);
		      fwrite(&blockLen, sizeof(int), 1, fout);
		    }
		}
	      fread(buf, sizeof(float), NWORD, f);
	      fwrite(buf, sizeof(float), NWORD, fout);
	      sblockcount++;
	      if (sblockcount == NSUBBLOCK)
		{
		  sblockcount = 0;
		  fwrite(&blockLen, sizeof(int), 1, fout);
		  fwrite(&blockLen, sizeof(int), 1, fout);
		}
	    }
	  else if (!strcmp("EVTE", blockName))
	    {
	      if ( partcount != 0 )
		{
		  for ( m = 0; m < NPART; m++)
		    buf3[m] = 0.;
		  for (m = 0; m < NSENTENCE - partcount; m++)
		    fwrite(buf3, sizeof(float), NPART, fout);
		  partcount = 0;
		  sblockcount++;
		  if ( sblockcount == NSUBBLOCK )
		    {
		      sblockcount = 0;
		      fwrite(&blockLen, sizeof(int), 1, fout);
		      fwrite(&blockLen, sizeof(int), 1, fout);
		    }
		}
	      nEVTE++;
	      fread(buf, sizeof(float), NWORD, f);
	      fwrite(buf, sizeof(float), NWORD, fout);
	      sblockcount++;
	      if (sblockcount == NSUBBLOCK)
		{
		  sblockcount = 0;
		  fwrite(&blockLen, sizeof(int), 1, fout);
		  fwrite(&blockLen, sizeof(int), 1, fout);
		} 
	    }
	  else if (!strcmp("RUNE", blockName))
	    {
	      if ( partcount != 0 )
		{
		  for ( m = 0; m < NPART; m++)
		    buf3[m] = 0.;
		  for (m = 0; m < NSENTENCE - partcount; m++)
		    fwrite(buf3, sizeof(float), NPART, fout);
		  partcount = 0;
		  sblockcount++;
		  if ( sblockcount == NSUBBLOCK )
		    {
		      sblockcount = 0;
		      fwrite(&blockLen, sizeof(int), 1, fout);
		      fwrite(&blockLen, sizeof(int), 1, fout);
		    }
		}
	      nRUNE++;
	      fread(buf, sizeof(float), NWORD, f);
	      fwrite(buf, sizeof(float), NWORD, fout);
	      sblockcount++;
	      if ( sblockcount != NSUBBLOCK )
		{
		  for ( m = 0; m < NWORD; m++)
		    buf[m] = 0.;
		  for (m = 0; m < NSUBBLOCK - sblockcount; m++)
		    fwrite(buf, sizeof(float), NWORD, fout);
		}
	      fwrite(&blockLen, sizeof(int), 1, fout);
	      fclose(f);
	      fclose(fout);
	      fill_vem();
	      fprintf(stderr, "RUNH: %d, EVTH: %d, PARTSUB: %d, LONG: %d, EVTE: %d, RUNE: %d\n",
		     nRUNH, nEVTH, nPARTSUB, nLONG, nEVTE, nRUNE);
	      return count2;
	    }
	  else
	    {
	      for (j = 0; j < 39; j++)
		{
		  nPARTSUB++;
		  fread(buf3, sizeof(float), NPART, f);
		  if (fabsf(buf3[4]) < (float)(100*DISTMAX) &&
		      fabsf(buf3[5]) < (float)(100*DISTMAX) &&
//		      hypotf(buf3[4],buf3[5]) < (float)(100*DISTMAX) &&
		      buf3[0] >= 1000. && buf3[0]  < 26000. &&
		      buf3[6] > 1.e4)
		    {
		      m = (int)((buf3[4]+(float)(100*DISTMAX))/600.);
		      n = (int)((buf3[5]+(float)(100*DISTMAX))/600.);
		      k = (int)(( buf3[6] - time1[m][n] - 
				  (float)(NT*DT*tcount))/DT);
		      if ( buf3[6] >= time1[m][n]+(float)(NT*DT*tcount)
			   && buf3[6] < 
			   time1[m][n]+(float)(NT*DT*(tcount+1)))
			{
			  energy = hypotf(buf3[3], 
					  hypotf(buf3[1],buf3[2]));
			  sectheta = energy/buf3[3];
			  energy = hypotf(pmass[(int)(buf3[0]/1000.)],
					  energy) -
			    pmass[(int)(buf3[0]/1000.)];
			  k = (int)(( buf3[6] - time1[m][n] - 
				      (float)(NT*DT*tcount))/(float)DT);
			  if (energy > emin/1.e6) 
			    {
			      count2++;
			    }
			  if ((int)vemcount[m][n][k][0] < 60000 && 
			      (int)vemcount[m][n][k][1] < 60000 &&
			      energy > emin/1.e6 )
			    {
			      get_elosses((int)(buf3[0]/1000), 
					  energy*1000., sectheta, 
					  &vem_tmp[0], &vem_tmp[1]);
			      gauss(gp);
			      vem_tmp[0] *= 1.+0.07*gp[0];
			      vem_tmp[1] *= 1.+0.07*gp[1];
			      vemcount[m][n][k][0] += 
				(unsigned short) rintf((float)vem_tmp[0]/VEM*100.);
			      pz[m][n][k] += (unsigned short)
				rintf(((float)vem_tmp[0]/VEM*100.)/sectheta/2.);
			      vemcount[m][n][k][1] +=
				(unsigned short) rintf((float)vem_tmp[1]/VEM*100.);
			      pz[m][n][k] += (unsigned short)
				rintf(((float)vem_tmp[1]/VEM*100.)/sectheta/2.);
			    }
			}
		      else if ( buf3[6] >= 
				time1[m][n]+(float)(NT*DT*(tcount+1)))
			{
			  fwrite(buf3, sizeof(float), NPART, fout);
			  partcount++;
			  if (partcount == NSENTENCE) 
			    {
			      partcount = 0;
			      sblockcount++;
			      if ( sblockcount == NSUBBLOCK ) 
				{
				  sblockcount = 0;
				  fwrite(&blockLen, sizeof(int), 1, fout);
				  fwrite(&blockLen, sizeof(int), 1, fout);
				}
			    }
			}
		    }		      
		}
	    }
	}
      fread(&blockLen, sizeof(int), 1, f);
    }
  fclose(f);
  fclose(fout);
  fill_vem();
  fprintf(stderr, "RUNH: %d, EVTH: %d, PARTSUB: %d, LONG: %d, EVTE: %d, RUNE: %d\n",
	  nRUNH, nEVTH, nPARTSUB, nLONG, nEVTE, nRUNE);
  return count2;
}

void fill_vem()
{

  int m=NX/2, n, m1, n1, i, j;
  float dist, vem_tmp, x, y, x2, y2, pz_tmp, sectheta, zencor;
  sectheta=1/cosf(zenith);
  for ( m = NX/2-dm; m < NX/2+dm; m++)
    {
      for ( n = NY/2-dn; n < NY/2+dn; n++)
	{
	  x = (float)m*6.0 - (float)DISTMAX + 3.0;
	  y = (float)n*6.0 - (float)DISTMAX + 3.0;
	  dist = hypotf( x, y );
	  zencor = hypotf( x/sectheta, y)/dist;
	  if ( dist  < filldist )
	    {
	      x2 = x/dist*(filldist+7.5);
	      y2 = y/dist*(filldist+7.5);
	      m1 = (int)((x2+(float)DISTMAX)/6.);
	      n1 = (int)((y2+(float)DISTMAX)/6.);
	      for ( i = 0; i < NT; i++ )
		{
		  for ( j = 0; j < 2; j++)
		    {
		      vem_tmp = (float) vemcount[m1][n1][i][j]*
			powf((filldist+7.5)/dist, 2.6)*
			expf(zencor*(filldist+7.5-dist)/575.);
		      if (vem_tmp > 60000.) vem_tmp = 60000.;
		      vemcount[m][n][i][j] = (unsigned short)vem_tmp;
		    }
		  pz_tmp = (dist/(filldist + 7.5)*(float)pz[m1][n1][i]/
			    ((float)vemcount[m1][n1][i][0]+
			     (float)vemcount[m1][n1][i][1])*2.+
			    (1. - dist/(filldist + 7.5))*cosf(zenith))*
		    ((float)vemcount[m][n][i][0]+
		     (float)vemcount[m][n][i][1])/2.;
		  pz[m][n][i]=(unsigned short)pz_tmp;
		}
	    }
	}
    }
}

void
gauss(double pair[])
{
  double r, phi;
  r = sqrt(-2.0*log(drand48()));
  phi = 2*PI*drand48();
  pair[0] = (r*cos(phi));
  pair[1] = (r*sin(phi));
  return;
}

