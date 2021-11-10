#include "nuf.h"

/************  CLASS FOR HANDLING THE PROGRAM ARGUMENTS *************************************************************/

CmdOptions::CmdOptions() {}

CmdOptions::~CmdOptions() {}

bool CmdOptions::getFromCmdLine(int argc, char **argv) {  
  char inBuf[sd_fname_size];
  char infile[sd_fname_size];
  FILE *wantFl;                  // For reading the want file
  int input_count = 0;
  
  if(argc==1) 
    {    
      fprintf(stdout, 
	      "\nUsage: %s [-v] [-option=value,...] fname,...\n",
	      argv[0]);
      fprintf(stdout,"    fname: DST file or txt list file name\n"); 
      fprintf(stdout,"    Must be run on Rutgers pass1 or pass2\n");
      fprintf(stdout,"    -d=yymmdd -t=hhmmss   fix event date and time\n");
      fprintf(stdout,"    -ndet=N   N detectors or more\n");    
      fprintf(stdout,"    -cosm     CIC+COSMOS Energy formula (default: CIC+CORSIKA)\n");    
      fprintf(stdout,"    -plot     plot gnu files (implies -gnu)\n");
      fprintf(stdout,"    -geom     refit geometry with fixed core after joint fit\n");
      fprintf(stdout,"    -skip=n   take only every nth event\n");
      fprintf(stdout,"    -Emin=E -Emax=E    take only events with E_mc>=(<)E,EeV\n");
      fprintf(stdout,"    -thetaminmc=R -thetamaxmc=R\n");
      fprintf(stdout,"    -rlost    list MC events lost by reconstruction\n");
      fprintf(stdout,"    -junk     include events without Rutgers plane fit\n");
      fprintf(stdout,"    -baddet/-nobaddet  always/never include detectors with igsd=1\n");
      fprintf(stdout,"    -gnu      create gnuplot files (implies -dtf)\n");
      fprintf(stdout,"    -v        verbose\n");
      fprintf(stdout,"    -fitdebug plot on each step of the fit (implies -plot)\n");
      fprintf(stdout,"    -dontuse  check calibev.donUse flag\n");
      fprintf(stdout,"    -c500     cut counters with r<500m (only for MC)\n");
      fprintf(stdout,"    attic/test options: -mcdt, -sdii, -tstalive -fiteta\n");
      fprintf(stdout,"                        -tstchi2 -desaturate -dtf -tonly\n");
      return false;
    }
  for(int i=1; i<argc; i++) {
      if(argv[i][0]=='-') { // option
	char *pos;
	if( (pos = strchr(argv[i], '=')) ) {
	  *pos = 0;
	  opt.insert(TStrStrPair(argv[i]+1, pos+1));
	}
	else {
	  opt.insert(TStrStrPair(argv[i]+1, "Y"));
	}
      }
      else { // DST or list file name
	if(strstr(argv[i], ".dst")) {
	  pushFile(argv[i]);
	  input_count++;
	}
	else {
	  if((wantFl=fopen(argv[i],"r"))==NULL) {
	    fprintf(stderr,"Can't open list file %s\n", argv[i]);
	  }
	  else {
	    while(fgets(inBuf, sd_fname_size, wantFl)) {
	      sscanf(inBuf,"%s",infile);
	      pushFile(infile);
	      input_count++;
	    }
	    fclose(wantFl);
	  }
	}
      }
  }

  if(isset("fitdebug")) {
    opt["plot"] = opt["fitdebug"];
  }

  if(isset("plot")) {
    opt["gnu"] = opt["plot"];
  }

  if(isset("gnu")) {
    opt["dtf"] = opt["gnu"];
  }

  return input_count;
}

bool CmdOptions::isset(std::string key) {
  TStrStrMap::iterator cur = opt.find(key);
  if(cur == opt.end()) {
    return false;
  }
  else {
    return true;
  }
}

std::string CmdOptions::get(std::string key) {
  TStrStrMap::iterator cur = opt.find(key);
  if(cur == opt.end()) {
    return "";
  }
  else {
    return cur->second;
  }
}


void CmdOptions::printOpts() {
  TStrStrMap::iterator p;
  for(p = opt.begin(); p != opt.end(); ++p) {
    printf("OPTION: %s=%s\n", p->first.c_str(), p->second.c_str());
  }
}




