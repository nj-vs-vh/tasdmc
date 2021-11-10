#define MAIN
#include "nuf.h"


/*************************************************************
nuf - neutrino finder by Grigory Rubtsov, grisha@ms2.inr.ac.ru
      based on the sditerator by Dmitry Ivanov      
**************************************************************/

int main(int argc, char **argv)
{
  SDrunClass sdrun;              // to handle the run DST files 
  char *dInFile;                 // pass1 dst input files
  FILE *fl;                      // dummy file pointer, for checking if the files exist

  // parses cmd line
  if(!cmd_opt.getFromCmdLine(argc,argv)) 
    return -1;

  if(cmd_opt.isset("dtf")) {
    mkdir(OUTDIR, 0755);
  }

  
  // Go over each run DST files and analyze the events/monitoring cycles in them.
  while((dInFile=pullFile()))
    {
      fprintf(stdout,"%s\n", "DATA FILE:");
      fprintf(stdout,"%s\n",dInFile);

      // Make sure that the input files exist, since right now, DST opener 
      // doesn't check it, in the case of .gz files.
      if((fl=fopen(dInFile,"r"))==NULL)
	{
	  pIOerror;
	  fprintf(stderr,"Can't open %s\n",dInFile);
	  return -1;
	}
      fclose(fl);
      
      if(!sdrun.openDSTfile(dInFile)) return -1;       // Open event DST file
      
      while(sdrun.readEvent())	{ // Go over all the events in the run.
	  iter(sdrun);
      }       
      sdrun.closeDSTfile();  // close pass1 event DST files.
      
    }

  fprintf(stdout,"\n\nDone\n");
  return 0;
}
