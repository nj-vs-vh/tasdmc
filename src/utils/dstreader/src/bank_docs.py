generated_bank_docs = {

"rusdraw_": """
integer4 event_num;		                        /* event number */
integer4 event_code;                                  /* 1=data, 0=Monte Carlo */
integer4 site;                                        /* BR=0,LR=1,SK=2,BRLR=3,BRSK=4,LRSK=5,BRLRSK=6 */
integer4 run_id[3];                                   /* run number for [0]-BR,[1]-LR,[2]-SK, -1 if irrelevant */
integer4 trig_id[3];		                        /* event trigger id for each tower, -1 if irrelevant */
integer4 errcode;                                     /* should be zero if there were no readout problems */
integer4 yymmdd;		                        /* event year, month, day */
integer4 hhmmss;		                        /* event hour minut second */
integer4 usec;		                        /* event micro second */
integer4 monyymmdd;                                   /* yymmdd at the beginning of the mon. cycle used in this event */
integer4 monhhmmss;                                   /* hhmmss at the beginning of the mon. cycle used in this event */
integer4 nofwf;		                        /* number of waveforms in the event */
/* These arrays contain the waveform information */
integer4 nretry[RUSDRAWMWF];                          /* number of retries to get the waveform */
integer4 wf_id[RUSDRAWMWF];                           /* waveform id in the trigger */
integer4 trig_code[RUSDRAWMWF];                       /* level 1 trigger code */
integer4 xxyy[RUSDRAWMWF];	                        /* detector that was hit (XXYY) */
integer4 clkcnt[RUSDRAWMWF];	                        /* Clock count at the waveform beginning */
integer4 mclkcnt[RUSDRAWMWF];	                        /* max clock count for detector, around 50E6 */
/* 2nd index: [0] - lower, [1] - upper layers */
integer4 fadcti[RUSDRAWMWF][2];	                /* fadc trace integral, for upper and lower */
integer4 fadcav[RUSDRAWMWF][2];                       /* FADC average */
integer4 fadc[RUSDRAWMWF][2][rusdraw_nchan_sd];	/* fadc trace for upper and lower */
/* Useful calibration information  */
integer4 pchmip[RUSDRAWMWF][2];     /* peak channel of 1MIP histograms */
integer4 pchped[RUSDRAWMWF][2];     /* peak channel of pedestal histograms */
integer4 lhpchmip[RUSDRAWMWF][2];   /* left half-peak channel for 1mip histogram */
integer4 lhpchped[RUSDRAWMWF][2];   /* left half-peak channel of pedestal histogram */
integer4 rhpchmip[RUSDRAWMWF][2];   /* right half-peak channel for 1mip histogram */
integer4 rhpchped[RUSDRAWMWF][2];   /* right half-peak channel of pedestal histograms */
/* Results from fitting 1MIP histograms */
integer4 mftndof[RUSDRAWMWF][2]; /* number of degrees of freedom in 1MIP fit */
real8 mip[RUSDRAWMWF][2];        /* 1MIP value (ped. subtracted) */
real8 mftchi2[RUSDRAWMWF][2];    /* chi2 of the 1MIP fit */
/*
1MIP Fit function:
[3]*(1+[2]*(x-[0]))*exp(-(x-[0])*(x-[0])/2/[1]/[1])/sqrt(2*PI)/[1]
4 fit parameters:
[0]=Gauss Mean
[1]=Gauss Sigma
[2]=Linear Coefficient
[3]=Overall Scalling Factor
*/
real8 mftp[RUSDRAWMWF][2][4];    /* 1MIP fit parameters */
real8 mftpe[RUSDRAWMWF][2][4];   /* Errors on 1MIP fit parameters */
""",

"rusdmc_": """
integer4 event_num;	 /* event number */
integer4 parttype;     /* Corsika particle code [proton=14, iron=5626,
for others, consult Corsika manual] */
integer4 corecounter;  /* counter closest to core */
integer4 tc;           /* clock count corresponding to shower front
passing through core position*/
real4 energy;          /* total energy of primary particle [EeV] */
real4 height;          /* height of first interation [cm] */
real4 theta;           /* zenith angle [rad] */
real4 phi;             /* azimuthal angle (N of E) [rad] */
real4 corexyz[3];      /* 3D core position in CLF reference frame [cm] */
""",
}
