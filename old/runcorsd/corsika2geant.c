/* readCorsika.c
 *
 * reads CORSIKA binary DAT files.
 *
 * It only dumps the few blocks that I am interested in, but can easily be
 * modified to do more. Assumptions about block sizes have been made on
 * how we ran CORSIKA here (e.g., THIN option is turned on). Written for
 * CORSIKA version 6.003.
 *
 * whanlon@cosmic.utah.edu
 * 29 jul 2006
 *
 * gcc -o readCorsika readCorsika.c -lm
 *
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

#include "corsika2geant.h"
#include "eloss_sdgeant.h"

int main(int argc, char **argv)
{
  FILE *f2;
  char outFile[256];
  char tmpFile[1000][256], geaFile[256];
  unsigned short buf[6];
  int i, j, m, n, tcount;
  double  count, count2;
  srand48(314159265);
  tcount = 0;
  count = count2 = 0.;
  if (argv[2] != NULL )
    sscanf(argv[2], "%f", &emin);
  else
    emin = 0.;
  printf("Energy threshold: %f keV\n", emin);
  fflush(stdout);
  strcpy (tmpFile[0], argv[1]);
  strcpy (geaFile, argv[2]);
  if ( load_elosses(geaFile) ==-1 )
    {
      fprintf (stderr, "Cannot open %s file\n", geaFile);
      return -1;
    }
  count = corsika_times(argv[1]);
  sprintf(outFile, "%s_gea.dat", argv[1]);
  f2 = fopen(outFile, "w");
  fwrite(eventbuf, sizeof(float), NWORD, f2);
  printf ("%g:%g\t %g Percent\n", count2, count, count2/count*100.);
  fflush(stdout);
  sprintf(tmpFile[1], "tmp%3.3d", 1); 
  count2 += corsika_vem_init(argv[1], tmpFile[1], tcount);
  printf ("%g:%g\t %g Percent\n", count2, count, count2/count*100.);
  fflush(stdout);
  for (m = 0; m < NX; m++)
    {
      for ( n = 0; n < NY; n++)
	{
	  if ( time1[m][n] != 1.e9 )
	    {
	      buf[0] = (unsigned short) m;
	      buf[1] = (unsigned short) n;
	      for ( i = 0; i < NT; i++ )
		{ 
		  if ( vemcount[m][n][i][0] > 0. ||
		       vemcount[m][n][i][1] > 0. ) 
		    {
		      buf[2] = vemcount[m][n][i][0];
		      buf[3] = vemcount[m][n][i][1];
		      buf[4] = (unsigned short) ((time1[m][n] + 
						  (float)(tcount*DT*NT) + 
						  (float)(i*DT) - tmin)/DT);
		      buf[5] = pz[m][n][i];
		      if ( buf[5] == 0 || 2*buf[5] > buf[2]+buf[3])
			buf[5] = (unsigned short)(cosf(zenith)*
						  (float)(buf[2]+buf[3])/2.);
		      fwrite(buf, sizeof(short), 6, f2);
		      
		    }
		}
	    }
	}
    }
  tcount++;
  for ( j = 1; j < (int)ceilf((float)TMAX/(float)NT); j++)
    {
      sprintf(tmpFile[j+1], "tmp%3.3d", j+1); 
      count2 += corsika_vem(tmpFile[j], tmpFile[j+1], tcount);
      printf ("%g:%g\t %g Percent\n", count2, count, count2/count*100.);
      fflush(stdout);
      for (m = 0; m < NX; m++)
	{
	  for ( n = 0; n < NY; n++)
	    {
	      if ( time1[m][n] != 1.e9 )
		{
		  buf[0] = (unsigned short) m;
		  buf[1] = (unsigned short) n;
		  for ( i = 0; i < NT; i++ )
		    { 
		      if ( vemcount[m][n][i][0] > 0. ||
			   vemcount[m][n][i][1] > 0. ) 
			{
			  buf[2] = vemcount[m][n][i][0];
			  buf[3] = vemcount[m][n][i][1];
			  buf[4] = (unsigned short) ((time1[m][n] + 
						     (float)(tcount*DT*NT) + 
						      (float)(i*DT) - tmin)/DT);
			  buf[5] = pz[m][n][i];
			  if ( buf[5] == 0 || 2*buf[5] > buf[2]+buf[3])
			    buf[5] = (unsigned short)(cosf(zenith)*
						      (float)(buf[2]+buf[3])/2.);
			  fwrite(buf, sizeof(short), 6, f2);

			}
		    }
		}
	    }
	}
      tcount++;
    }
  fclose(f2);
  exit(EXIT_SUCCESS);
}

