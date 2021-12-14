/*
 * eloss_sdgeant.c
 *
 *  Last update: Apr 19, 2010
 *      Author: Dmitri Ivanov <ivanov@physics.rutgers.edu>
 */

#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>

#include "event.h"
#include "./eloss_sdgeant.h"

#define ELOSS_SDGEANT_MAXBLIST 512 // maximum number of banks / event
#define ELOSS_SDGEANT_DSTUNIT 1    // dst input unit used to load the geant information
// maximum possible corsika ID ( if corsika ID is greater than this value then
// zeros for energy loss will be returned
#define ELOSS_SDGEANT_MAXCORID 1024

// number of particle types that are supported or might be supported in the future
#define ELOSS_SDGEANT_NPARTICLES (ELOSS_SDGEANT_MAXCORID + 1)

// maximum possible sec(theta) beyond which won't extrapolate
#define ELOSS_SDGEANT_MAX_ALLOWED_SECTHETA 10.0

// zero on the log scale
#define ELOSS_SDGEANT_LOGSCALE_ZERO -10.0

// mandatory CORSIKA IDs; they must be present in the dst file
#define ELOSS_SDGEANT_NCORID_NEEDED 9
static int eloss_sdgeant_corid_to_check[ELOSS_SDGEANT_NCORID_NEEDED] = {1, 2, 3, 5, 6, 8, 9, 13, 14};

// to indicate that the geant library has been loaded
static int eloss_sdgeant_loaded = 0;

typedef struct
{

    integer4 ike; // kinetic energy index, log10(K.E./MeV)

    // Energy loss probability proportionality constants for log10(KE/MeV)
    // dependence
    real8 peloss_kepc[SDGEALIB_NSECTHETA];

    // Energy loss probability proportionality constants for sec(theta)
    // dependence
    real8 peloss_sepc[SDGEALIB_NSECTHETA];

    // Peak channel energy loss proportionality constants for log10(KE/MeV)
    // dependence, [0] - lower, [1] - upper layers
    real8 pkeloss_kepc[SDGEALIB_NSECTHETA][2];

    // Peak channel energy loss proportionality constants for sec(theta)
    // dependence, [0] - lower, [1] - upper layers
    real8 pkeloss_sepc[SDGEALIB_NSECTHETA][2];

    real8 peloss[SDGEALIB_NSECTHETA]; // probability of non-zero energy loss

    integer4 nn0bins[SDGEALIB_NSECTHETA]; // number of non-zero energy loss bins

    sdgealib_bin_struct *bins[SDGEALIB_NSECTHETA]; // non-zero energy loss bins

} eloss_sdgeant_ke_bin_struct;

typedef struct
{
    int nke; // number of log10 KE/MeV bins

    double log10kemin; // minimum log10(KE/MeV) for binning

    double log10kemax; // maximum log10(KE/MeV) for binning

    double log10kebs; // bin size for log10(KE/MeV) binning

    int nsectheta; // number of sec(theta) bins

    double secthetamin; // minimum sec(theta) for binning

    double secthetamax; // maximum sec(theta) for binning

    double secthetabs; // bin size for sec(theta) binning

    eloss_sdgeant_ke_bin_struct *ke; // energy loss histograms for each log10 KE/MeV kinetic energy bin

    char ok2free; // safety; indicates that it is OK to free the pointers for this particle (they have been allocated)

} eloss_sdgeant_particle_info_struct;

// particles are labeled by their corsika ID
// memory waste is very insignificant
static eloss_sdgeant_particle_info_struct eloss_sdgeant_particle[ELOSS_SDGEANT_NPARTICLES];

// to sample log10(ELOSS/MeV) bins
static void sample_2dbins_log10eloss(int nbins, sdgealib_bin_struct *bins, double *log10_elossUpper,
                                     double *log10_elossLower);

static void printErr(const char *form, ...);

int load_elosses(const char *geantfname)
{
    FILE *fl;
    integer4 inUnit, wantBanks, gotBanks, mode, rc, event, size;
    int ievent, iparticle, ike, isectheta, ibin, ilayer;

    int ncorid;
    int icorid;
    int corid = 0;   // current particle that's being read out
    int nke_cnt = 0; // to count the number of energy loss histograms (by KE binning)

    // assigning shorter names to the structures in the local scope, for simplicity
    sdgealib_head_struct *head = &sdgealib_head_;
    sdgealib_pinf_struct *pinf = &sdgealib_pinf_;
    sdgealib_hist_struct *hist = &sdgealib_hist_;
    eloss_sdgeant_particle_info_struct *par = eloss_sdgeant_particle;
    eloss_sdgeant_ke_bin_struct *ke;

    if (eloss_sdgeant_loaded != 0)
    {
        printErr("load_elosses: WARNING: energy loss histograms are already loaded");
        return 0;
    }

    fl = fopen(geantfname, "r");
    if (fl == NULL)
    {
        printErr("load_elosses: can't open %s for reading", geantfname);
        return -1;
    }

    // Zeroing out the energy loss information for all particles
    // (nothing has been allocated yet so it is OK to set all pointers in the structures to zeros)
    for (iparticle = 0; iparticle < ELOSS_SDGEANT_NPARTICLES; iparticle++)
        memset(&par[iparticle], 0, sizeof(eloss_sdgeant_particle_info_struct));

    size = ELOSS_SDGEANT_MAXBLIST;
    wantBanks = newBankList(size);
    gotBanks = newBankList(size);
    addBankList(wantBanks, SDGEALIB_BANKID);

    mode = MODE_READ_DST;
    inUnit = ELOSS_SDGEANT_DSTUNIT;
    rc = dstOpenUnit(inUnit, geantfname, mode);
    if (rc != SUCCESS)
    {
        printErr("load_elosses: can't dst-open (unit %d) %s", inUnit, geantfname);
        return -1;
    }
    ievent = 0;
    // load the geant information from the DST file
    while ((rc = eventRead(inUnit, wantBanks, gotBanks, &event)) > 0)
    {
        if (!event)
        {
            printErr("load_elosses: corrupted geant library information in %s\n", geantfname);
            return -1;
        }
        if (!tstBankList(gotBanks, SDGEALIB_BANKID))
        {
            printErr("load_elosses: sdgealib bank absent for dst ievent = %d in %s", ievent, geantfname);
            return -1;
        }

        if (head->itype == SDGEALIB_HIST && corid != head->corid)
        {
            printErr("load_elosses: histogram information arrived before the particle information!");
            return -1;
        }

        // particle information
        if (head->itype == SDGEALIB_PINF)
        {
            if (head->corid < 1 || head->corid > ELOSS_SDGEANT_MAXCORID)
            {
                printErr("load_elosses: read out a wrong CORSIKA ID %d", head->corid);
                return -1;
            }

            // if a particle has been read out and about to read out a next particle
            if (corid != 0)
            {
                if (nke_cnt != par[corid].nke)
                {
                    printErr(
                        "load_elosses: corid = %d: number of KE bins %d in the  particle information doesn't match the number of KE bins read out %d",
                        corid, par[corid], nke_cnt);
                    return -1;
                }
            }

            corid = head->corid; // saving the particle type that's being currently read out
            nke_cnt = 0;         // reset the number of KE bin histogram counter

            // particle binning information
            par[corid].nke = pinf->nke;
            par[corid].log10kemin = pinf->log10kemin;
            par[corid].log10kemax = pinf->log10kemax;
            par[corid].log10kebs = (par[corid].log10kemax - par[corid].log10kemin) / ((double)par[corid].nke);
            par[corid].nsectheta = pinf->nsectheta;
            par[corid].secthetamin = pinf->secthetamin;
            par[corid].secthetamax = pinf->secthetamax;
            par[corid].secthetabs = (par[corid].secthetamax - par[corid].secthetamin) / ((double)par[corid].nsectheta);

            // allocating space for log10(KE/MeV) arrays
            par[corid].ke = (eloss_sdgeant_ke_bin_struct *)calloc(par[corid].nke, sizeof(eloss_sdgeant_ke_bin_struct));
            if (!par[corid].ke)
            {
                printErr("load_elosses: failed to allocate memory for log10(KE/MeV) bins, corid = %d", corid);
                return -1;
            }
            else
                par[corid].ok2free = 1;

            // load the energy loss interpolation rules
            for (ike = 0; ike < par[corid].nke; ike++)
            {
                ke = &par[corid].ke[ike];
                for (isectheta = 0; isectheta < par[corid].nsectheta; isectheta++)
                {
                    ke->peloss_kepc[isectheta] = pinf->peloss_kepc[ike][isectheta];
                    ke->peloss_sepc[isectheta] = pinf->peloss_sepc[ike][isectheta];
                    for (ilayer = 0; ilayer < 2; ilayer++)
                    {
                        ke->pkeloss_kepc[isectheta][ilayer] = pinf->pkeloss_kepc[ike][isectheta][ilayer];
                        ke->pkeloss_sepc[isectheta][ilayer] = pinf->pkeloss_sepc[ike][isectheta][ilayer];
                    }
                }
            }
        }
        // energy loss histograms
        else if (head->itype == SDGEALIB_HIST)
        {
            if (corid != head->corid)
            {
                printErr("load_elosses: energy loss histogram corid=%d but the particle information corid = %d",
                         head->corid, corid);
                return -1;
            }
            if (hist->ike < 0 || hist->ike >= par[corid].nke)
            {
                printErr("load_elosses: corid = %d: invalid KE index = %d in the dst file, must be in 0 - %d range",
                         corid, hist->ike, 0, par[corid].nke - 1);
                return -1;
            }

            ike = hist->ike;
            ke = &par[corid].ke[ike];

            for (isectheta = 0; isectheta < par[corid].nsectheta; isectheta++)
            {
                ke->peloss[isectheta] = hist->peloss[isectheta];
                ke->nn0bins[isectheta] = hist->nn0bins[isectheta];
                // allocating space for the energy loss bins
                ke->bins[isectheta] = (sdgealib_bin_struct *)calloc(ke->nn0bins[isectheta], sizeof(sdgealib_bin_struct));
                if (!ke->bins[isectheta])
                {
                    printErr(
                        "load_elosses: failed to allocate memory for the energy loss bins, corid = %d ike = %d isectheta = %d nbins = %d",
                        corid, ike, isectheta, ke->nn0bins[isectheta]);
                    return -1;
                }
                for (ibin = 0; ibin < ke->nn0bins[isectheta]; ibin++)
                {
                    ke->bins[isectheta][ibin].ix = hist->bins[isectheta][ibin].ix;
                    ke->bins[isectheta][ibin].iy = hist->bins[isectheta][ibin].iy;
                    ke->bins[isectheta][ibin].w = hist->bins[isectheta][ibin].w;
                }
            }
            nke_cnt++; // count how many histogram information pieces were loaded
        }
        else
        {
            printErr("load_elosses: sdgealib information type %d not understood in %s dst ievent = %d", head->itype,
                     geantfname, ievent);
            return -1;
        }

        ievent++;
    }

    // in case mu+, mu- are to be treated in the same way ( energy loss info available for one but not the other)
    if (par[5].nke == 0 && par[6].nke > 0)
    {
        memcpy(&par[5], &par[6], sizeof(eloss_sdgeant_particle_info_struct));
        // the pointers for this particle are copied too
        // so by de-allocating them in for the parent particle automatically de-allocates
        // them for the particle for which we copied the information from the parent particle
        par[5].ok2free = 0;
    }
    else
    {
        memcpy(&par[6], &par[5], sizeof(eloss_sdgeant_particle_info_struct));
        par[6].ok2free = 0;
    }
    // clean up the DST I/O
    clrBankList(wantBanks);
    clrBankList(gotBanks);
    delBankList(wantBanks);
    delBankList(gotBanks);
    dstCloseUnit(inUnit);

    // check that the mandatory CORSIKA IDs have been successfully loaded:
    ncorid = 0;
    for (icorid = 0; icorid < ELOSS_SDGEANT_NCORID_NEEDED; icorid++)
    {
        corid = eloss_sdgeant_corid_to_check[icorid];
        if (par[corid].nke > 0)
            ncorid++;
        else
            printErr("load_elosses: particle corid=%d energy loss info not found in %s", corid, geantfname);
    }

    if (ncorid < ELOSS_SDGEANT_NCORID_NEEDED)
        return -1;

    // ************************************************************
    //
    //  RANDOM SEED SET TO THE CURRENT SYSTEM TIME
    //
    // ************************************************************
    srand48(time(NULL));

    // everything is good
    eloss_sdgeant_loaded = 1;
    return 0;
}

int get_elosses(int corid, double ke, double sectheta, double *elossUpper, double *elossLower)
{
    eloss_sdgeant_particle_info_struct *par = 0;
    static const double ln10 = 2.3025850929940456840179914546843642;
    double log10ke;                                             // log10 (KE/MeV)
    double log10ke_bc;                                          // log10(KE/MeV) bin center value
    double sectheta_bc;                                         // sec(theta) bin center value
    int ikelo, ike, ikeup, isecthetalo, isectheta, isecthetaup; // ke, sec(theta) indices
    double peloss;                                              // (interpolated) energy loss probability
    int ilayer;
    double log10_eloss[2];
    // make sure geant library has been loaded
    if (eloss_sdgeant_loaded == 0)
    {
        (*elossUpper) = 0.0;
        (*elossLower) = 0.0;
        printErr("get_elosses: geant library is not currently loaded; call load_elosses");
        return -1;
    }

    // CORSIKA ID is bad;  print error message & prevent the index overflow
    if (corid < 0)
    {
        printErr("get_elosses: invalid CORSIKA ID: %d", corid);
        (*elossUpper) = 0.0;
        (*elossLower) = 0.0;
        return -1;
    }

    // CORSIKA IDs that are too large are clearly not supported;  prevent the array index overflow
    if (corid > ELOSS_SDGEANT_MAXCORID)
    {
        (*elossUpper) = 0.0;
        (*elossLower) = 0.0;
        return 0;
    }

    par = &eloss_sdgeant_particle[corid]; // particle that we're working with

    // if a given corsika ID particle doesn't have the geant information, set
    // all energy losses to zero
    if (par->nke < 1)
    {
        (*elossUpper) = 0.0;
        (*elossLower) = 0.0;
        return 0;
    }

    // no energy loss if the particle KE is below the minimum energy threshold
    log10ke = log(ke) / ln10;
    if (log10ke < par->log10kemin)
    {
        (*elossUpper) = 0.0;
        (*elossLower) = 0.0;
        return 0;
    }

    // make sure sec(theta) is good for interpolation / extrapolation
    if (sectheta < 1.0)
        sectheta = 1.0;
    if (sectheta > ELOSS_SDGEANT_MAX_ALLOWED_SECTHETA)
        sectheta = ELOSS_SDGEANT_MAX_ALLOWED_SECTHETA;

    // decide from which energy loss histograms should sample
    ike = (int)floor((log10ke - par->log10kemin) / par->log10kebs);
    if (ike < 0)
        ike = 0;
    if (ike > (par->nke - 1))
        ike = (par->nke - 1);

    if (log10ke < (par->log10kemin + ((double)ike + 0.5) * par->log10kebs))
    {
        ikelo = ((ike < 1) ? ike : (ike - 1));
        ikeup = ike;
    }
    else
    {
        ikelo = ike;
        ikeup = ((ike == (par->nke - 1)) ? ike : (ike + 1));
    }

    // in deciding which K.E. index it is better to use for sampling we use a probabilistic approach:
    // the closest bin center value is more probable, unless we are on the edges of the log10(K.E/MeV) range
    // then we have to use the edge values
    if (ikelo < ikeup)
        ike = ((drand48() < (log10ke - par->log10kemin - ((double)ikelo + 0.5) * par->log10kebs) / par->log10kebs) ? ikeup
                                                                                                                   : ikelo);

    isectheta = (int)floor((sectheta - par->secthetamin) / par->secthetabs);
    if (isectheta < 0)
        isectheta = 0;
    if (isectheta > (par->nsectheta - 1))
        isectheta = (par->nsectheta - 1);
    if (sectheta < (par->secthetamin + ((double)isectheta + 0.5) * par->secthetabs))
    {
        isecthetalo = ((isectheta < 1) ? isectheta : (isectheta - 1));
        isecthetaup = isectheta;
    }
    else
    {
        isecthetalo = isectheta;
        isecthetaup = ((isectheta == (par->nsectheta - 1)) ? isectheta : (isectheta + 1));
    }
    if (isecthetalo < isecthetaup)
        isectheta = ((drand48() < (sectheta - par->secthetamin - ((double)isecthetalo + 0.5) * par->secthetabs) / par->secthetabs) ? isecthetaup : isecthetalo);

    // bin center values for log10ke, sec(theta) which correspond to energy loss histograms from which we sample
    log10ke_bc = par->log10kemin + ((double)ike + 0.5) * par->log10kebs;
    sectheta_bc = par->secthetamin + ((double)isectheta + 0.5) * par->secthetabs;

    // Get the energy loss probability and interpolate it:
    peloss = par->ke[ike].peloss[isectheta] + par->ke[ikelo].peloss_kepc[isectheta] * (log10ke - log10ke_bc) + par->ke[ike].peloss_sepc[isecthetalo] * (sectheta - sectheta_bc);

    // sample the probability that there is energy deposit in any of the layers; if doesn't pass, then
    // set the energy losses to zeros and return.
    if (peloss < drand48())
    {
        (*elossUpper) = 0.0;
        (*elossLower) = 0.0;
        return 0;
    }

    // sample the energy loss ( upper, lower)
    sample_2dbins_log10eloss(par->ke[ike].nn0bins[isectheta], par->ke[ike].bins[isectheta], &log10_eloss[1],
                             &log10_eloss[0]);

    // interpolate the energy loss
    for (ilayer = 0; ilayer < 2; ilayer++)
    {
        log10_eloss[ilayer] += par->ke[ikelo].pkeloss_kepc[isectheta][ilayer] * (log10ke - log10ke_bc);
        log10_eloss[ilayer] += par->ke[ike].pkeloss_sepc[isecthetalo][ilayer] * (sectheta - sectheta_bc);
    }

    // return the sampled values (linear, in MeV)
    (*elossUpper) = exp(log10_eloss[1] * ln10);
    (*elossLower) = exp(log10_eloss[0] * ln10);
    return 0;
}

void unload_elosses()
{
    int corid;
    int ike, isectheta;
    eloss_sdgeant_particle_info_struct *par = eloss_sdgeant_particle;
    if (eloss_sdgeant_loaded == 0)
        return;
    for (corid = 0; corid <= ELOSS_SDGEANT_MAXCORID; corid++)
    {
        if (par[corid].nke > 0)
        {
            if (par[corid].ok2free && par[corid].ke)
            {
                for (ike = 0; ike < par[corid].nke; ike++)
                {
                    for (isectheta = 0; isectheta < par[corid].nsectheta; isectheta++)
                    {
                        if (par[corid].ke[ike].bins[isectheta])
                            free(par[corid].ke[ike].bins[isectheta]);
                    }
                }
                free(par[corid].ke);
            }
            memset(&par[corid], 0, sizeof(eloss_sdgeant_particle_info_struct));
        }
    }
    eloss_sdgeant_loaded = 0;
}

void sample_2dbins_log10eloss(int nbins, sdgealib_bin_struct *bins, double *log10_elossUpper, double *log10_elossLower)
{

    // bin size in 2D energy loss histograms from which we do the sampling
    static const double bs = (SDGEALIB_LOG10ELOSSMAX - SDGEALIB_LOG10ELOSSMIN) / ((double)SDGEALIB_NLOG10ELOSS);

    int ibin;
    if (nbins < 1)
    {
        (*log10_elossUpper) = ELOSS_SDGEANT_LOGSCALE_ZERO;
        (*log10_elossLower) = ELOSS_SDGEANT_LOGSCALE_ZERO;
        return;
    }
    do
    {
        ibin = (int)floor(drand48() * (double)(nbins - 1) + 0.5);
    } while (SDGEALIB_MAXBVAL * drand48() > (double)bins[ibin].w);

    // bin size times index gives the left edge of the bin
    // we want x and y to be randomly distributed in the bins.
    // if either ix or iy is less than zero, this means that the energy loss happens
    // in one of the layers but not in the other.
    (*log10_elossUpper) = (bins[ibin].ix > -1 ? (SDGEALIB_LOG10ELOSSMIN + bs * ((double)bins[ibin].ix + drand48()))
                                              : ELOSS_SDGEANT_LOGSCALE_ZERO);
    (*log10_elossLower) = (bins[ibin].iy > -1 ? (SDGEALIB_LOG10ELOSSMIN + bs * ((double)bins[ibin].iy + drand48()))
                                              : ELOSS_SDGEANT_LOGSCALE_ZERO);
}

void printErr(const char *form, ...)
{
    char mess[0x400];
    va_list args;
    va_start(args, form);
    vsprintf(mess, form, args);
    va_end(args);
    fprintf(stderr, "eloss_sdgeant: %s\n", mess);
}
