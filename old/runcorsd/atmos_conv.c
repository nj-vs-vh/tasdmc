#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>
#include "atmos_conv.h"

double h2mo( double h, int model)
{
  int i=0;
  double mo=0.;

  while ( i < NHEIGHT-1 && h > atm_height[model][i+1]*1.e5 ) i++;
  if ( i < NHEIGHT-1)
    mo = atm_par[model][i][0] + atm_par[model][i][1]*
      exp(-h/atm_par[model][i][2]);
  else
    mo = atm_par[model][i][0] - atm_par[model][i][1]*h/atm_par[model][i][2];
  return mo;
}

double mo2h( double mo, int model)
{
  int i=0;
  double h=0.;

  while ( i < NHEIGHT-1 && mo < h2mo(atm_height[model][i+1]*1.e5, model) ) i++;
  if ( i < NHEIGHT-1)
    h = -atm_par[model][i][2]*
      log((mo - atm_par[model][i][0])/atm_par[model][i][1]);
  else
    h = (atm_par[model][i][0] - mo)*atm_par[model][i][2]/atm_par[model][i][1];
  return h;
}

double density_atmos( double h, int model)
{
  int i=0;
  double density=0.;

  while ( i < NHEIGHT-1 && h > atm_height[model][i+1]*1.e5) i++;
  if ( i < NHEIGHT-1)
    density = atm_par[model][i][1]/atm_par[model][i][2]*
      exp(-h/atm_par[model][i][2]);
  else
    density = atm_par[model][i][1]/atm_par[model][i][2];
  if ( density < 0. ) density = 0.;
  return density;
}

