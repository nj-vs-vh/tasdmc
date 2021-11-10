#ifndef _nuf_h_
#define _nuf_h_

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "event.h"
#include "filestack.h"
#include "sduti.h"
#include <algorithm>
#include <vector>
#include <iostream>
#include <gsl/gsl_fit.h>

#include "sdrunclass.h"
#include "cmdoptions.h"
#include "sign.h"

/*********************************  GLOBAL CPP DEFINITIONS **********************************************************/

// lenght of the file names
#define sd_fname_size 1024

// to print I/O error messages
#define pIOerror fprintf(stderr,"\nI/O Erorr: ")

#define OUTDIR "nuf_out" // output directory
#define gp_maxcmd 60000

#define UNIT 1200.0e2
#define r_X 0.666667 // 800 m
#define s_RMINCUT 0.25	// 300 m
#define s_RMAXCUT 1.5	// 1800 m
#define NSEC 2.49827e-4  // 1ns = 2.5e-4*1200m
#define DET_AREA 3.0 // detector area, 3m^2
#define DEG (M_PI/180.0)

#ifdef MAIN
CmdOptions cmd_opt;                 // to handle the program arguments.
double fit_final_size;
#else
extern CmdOptions cmd_opt;
extern double fit_final_size;
#endif

extern void iter(SDrunClass sdrun);
extern void plot_dtf(double* init, double P);
extern void read_signals(double* init, int db_date, double db_time);
extern int myround(double f);

struct dtinfo {
  int xxyy;
  double r_plane;
  double r;
  bool zero;
};

extern bool dtinfo_cmp(dtinfo a, dtinfo b);
 
#endif
