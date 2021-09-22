
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define DISTMAX 8400 /* Meters */
#define NX DISTMAX/3
#define NY DISTMAX/3
#define NWORD 273

int main(int argc, char **argv)
{
  float eventbuf[NWORD];
  unsigned short buf[6];
  int parttype;
  float energy,height,theta,phi_orig;
  int m,n;
  float tmpedep[2];
  int tmptime;
  float pztmp;
  int n_problems=0;
  FILE *f = 0;  
  int verbosity=0;
  int have_stdin = 0;
  const char* infile="";
  int i=0;
  
    // go over the arguments if there are command line arguments
  for (i = 0; i < argc; i++)
    {
      if ( (argc == 1 ) ||   
	   (strcmp("-h",argv[i]) == 0) || 
	   (strcmp("--h",argv[i]) == 0) ||
	   (strcmp("-help",argv[i]) == 0) ||
	   (strcmp("--help",argv[i]) == 0) ||
	   (strcmp("-?",argv[i]) == 0) ||
	   (strcmp("--?",argv[i]) == 0) ||
	   (strcmp("/?",argv[i]) == 0))
        {     
	  fprintf(stderr,"\nProgram to check the integrity of the DAT????XX_gea.dat files\n");
	  fprintf(stderr,"\nUsage: %s -bin_f <DAT????XX_gea.dat>\n", argv[0]);
	  fprintf(stderr,"-bin_f   <str>: Binarry DAT????XX_gea.dat\n");
	  fprintf(stderr,"                (last 2 digits XX are the energy channel):\n");
	  fprintf(stderr,"                XX=00-25: energy from 10^18.0 to 10^20.5 eV\n");
	  fprintf(stderr,"                XX=26-39: energy from 10^16.6 to 10^17.9 eV\n");
	  fprintf(stderr,"                XX=80-85: energy from 10^16.0 to 10^16.5 eV\n");
	  fprintf(stderr,"--stdin:        Obtain the (binary) content of DAT????XX_gea.dat\n");
	  fprintf(stderr,"                through stdin\n");
	  fprintf(stderr,"-v       <int>: (Optional) Verbosity level, default is %d\n", verbosity);
	  fprintf(stderr,"\n");
          return 1;
        }
      else if(i < 1)
	continue;
      else if (strcmp("-bin_f", argv[i]) == 0)
        {
          if ((++i >= argc) || !argv[i] || (argv[i][0] == '-'))
            {
              fprintf(stderr, "error: -bin_f: specify the DAT????XX_gea.dat binary input file!\n");
              return 2;
            }
	  infile = argv[i];
        }
      else if (strcmp("-v", argv[i]) == 0)
        {
          if ((++i >= argc) || !argv[i] || (argv[i][0] == '-'))
            {
              fprintf(stderr, "error: -v: specify the verbosity level!\n");
              return 2;
            }
	  sscanf(argv[i], "%d", &verbosity);
        }
      else if (strcmp("--stdin", argv[i]) == 0)
	have_stdin = 1;
      else
        {
          fprintf(stderr, "error: %s: unrecognized option\n", argv[i]);
          return 2;
        }
    }
  if(have_stdin && strlen(infile))
    {
      fprintf(stderr,"error: both --stdin is provided and a file on the command line; can do only one input type at a time\n");
      return 2;
    }
  if(have_stdin)
    f=stdin;
  else
    {
      f=fopen(infile, "rb");
      if(!f)
	{
	  fprintf(stderr,"Error: file '%s' not found\n",infile);
	  return 2;
	}
    }
  if(!fread(eventbuf, sizeof(float), NWORD, f))
    {
      fprintf(stderr,"error: failed to read header from %s\n",infile);
      n_problems++;
      return n_problems;
    }
  parttype = (int)eventbuf[2];
  energy   = eventbuf[3]/1.e9;
  height   = eventbuf[6];
  theta    = eventbuf[10];
  phi_orig = eventbuf[11];
  if(verbosity >=1)
    {
      fprintf(stdout,"%s parttype=%d energy=%f height=%f theta=%f phi_orig=%f\n",
	      infile,parttype,energy,height,180.0/M_PI*theta,180.0/M_PI*phi_orig);
      fflush(stdout);
    }
  while (fread(buf,sizeof(short),6,f)==6)
    {
      m          = (int)buf[0];
      n          = (int)buf[1];
      if (m >= NX)
	{
	  if(verbosity>=2)
	    fprintf(stderr,"m=%d is too large, maximum is %d\n",m,NX-1);
	  n_problems++;
	}
      if (n >= NY)
	{
	  if(verbosity >=2)
	    fprintf(stderr,"n=%d is too large, maximum is %d\n",n,NY-1);
	  n_problems++;
	}      
      tmpedep[0] = (float)buf[2];
      tmpedep[1] = (float)buf[3];
      tmptime    = (int)buf[4];
      pztmp      = (float)buf[5];
      if(verbosity>=2)
	{
	  fprintf(stdout,"%5d %5d %6.3e %6.3e %5d %6.3e\n",m,n,tmpedep[0],tmpedep[1],tmptime,pztmp);
	  fflush(stdout);
	}
    }
  if(!have_stdin)
    fclose(f);
  if(n_problems==0)
    fprintf(stdout,"%s OK\n", infile);
  else
    fprintf(stdout,"%s FAIL\n",infile);
  fflush(stdout);
  return n_problems;
}
