#include "nuf.h"
#include "sdparamborder.h"
#include "br_xxyy.h"
#include "lr_xxyy.h"
#include "sk_xxyy.h"
#include "fit.hpp"

#define Sbcount 5
#define Sb_b0 2.5
#define Sb_bstep 0.5

inline double Sb_b(int i) { return Sb_b0 + i*Sb_bstep; }
double Sb[5]; // arXiv:1104.3399, arXiv:1305.7439

int dcount;
double dvalue[RUFPTNMH][11]; // 0,1,2 - x,y,z; 3 - S, 4 - time, 5 - s_sigma2, 6 - t_sigma2, 7 - bad timing, 8 - pcnt, 9 - asymm, 10 - peak val
int dsaturated[RUFPTNMH];
int dxxyy[RUFPTNMH]; // xxyy for given detector

double AOPfitX[RUFPTNMH], AOPfitY[RUFPTNMH], AOPfitW[RUFPTNMH]; // for area over peak fit
int AOPcnt;
double AOPc0, AOPc1, AOPcov00, AOPcov01, AOPcov11, AOPchi2, AOP1200, AOP1200_err;

int dcount_nz, dcount_ng;
double corecounterX=1e6, corecounterY=1e6;

int gl_pcnt, gl_pcnt_largest, gl_largest_xxyy, gl_apcnt_u, gl_apcnt_l; // peak count
double gl_largest_signal, gl_ul_diff, gl_ul_sum;

double g_chi2L1, g_chi2L2, g_chi2L3, g_chi2Z, g_chi2T;
double g_NL1, g_NL2, g_NL3, g_NZ, g_NT; // chi2 split

int xxyy_0;
double signal_0; // max detector for zero detectors range

int anal = 2; // 0 - plane fit, 1 - modified Linsley, 2 - final
unsigned long long ev;
bool fiteta = false;
bool fitgeom = false;

void calc_errorbars(double *init);
double f_chi2(const gsl_vector *, void *);
double linsley_t(double r, double S);
double linsley_s(double r, double S);
double s_eta(double theta);
double desaturate(double S);
double s_profile(double r_ta, double theta, double eta, double r_plane);
double s_profile_tasimple(double r_ta, double theta, double eta);
double attenuation(double);
double estimatedE(double, double);
double logPua(double, double);
double inv_phi(double phi) { return phi<180?phi+180:phi-180; };
double mindist(int site, double xcore, double ycore);
double RMS_S(double S, double area);
bool load_zero(double rmax);
bool load_zero_tower(int tower, double rmax);
bool fix_site();

int xxyy_num[7];
int *xxyy[7];
int n_dataset;
 
/////////// EXECUTED ON EACH EVENT //////////////////////
void iter(SDrunClass sdrun){
  static int each=0;
  each++;
  if(cmd_opt.isset("skip")) {
    int skip = atoi(cmd_opt.get("skip").c_str());
    if(each%skip) return; // take only n-th
  }

  if(cmd_opt.isset("tonly")) {
    printf("%i %i %.6g %i %i %g SDTRIG %i\n",
	   20000000 + tasdcalibev_.date, tasdcalibev_.time, tasdcalibev_.usec/1.0e6,
	   rufptn_.nsclust, rufptn_.nstclust, rusdgeom_.theta[0], tasdcalibev_.trgMode);
    return;
  }

  if(rusdraw_.yymmdd<81112) {
    xxyy_num[0] = NBR_DS1;   xxyy_num[1] = NLR_DS1;  xxyy_num[2] = NSK_DS1; 
    xxyy[0] = br_xxyy_ds1; xxyy[1] = lr_xxyy_ds1; xxyy[2] = sk_xxyy_ds1;
    n_dataset =  1;
  }
  else { // 2nd dataset is still unmerged
    xxyy_num[0] = NBR_DS2;   xxyy_num[1] = NLR_DS2;  xxyy_num[2] = NSK_DS2; 
    xxyy[0] = br_xxyy_ds2; xxyy[1] = lr_xxyy_ds2; xxyy[2] = sk_xxyy_ds2;
    n_dataset = 2;
  }
  fix_site();

  if(rusdmc_.energy<1e-3 && tasdcalibev_.trgPos<=2) {
    return; // No hibrid trigger events in data
    // for Ben's MC trgPos==0 as for 2013-11-25
  }

  if(cmd_opt.isset("d") && atoi(cmd_opt.get("d").c_str()) != rusdraw_.yymmdd ) return;
  if(cmd_opt.isset("t") && atoi(cmd_opt.get("t").c_str()) != rusdraw_.hhmmss ) return;
  if(cmd_opt.isset("Emin") && rusdmc_.energy>1e-3 && rusdmc_.energy < atof(cmd_opt.get("Emin").c_str())) return;
  if(cmd_opt.isset("Emax") && rusdmc_.energy>1e-3 && rusdmc_.energy >= atof(cmd_opt.get("Emax").c_str())) return;
  if(cmd_opt.isset("thetaminmc") && rusdmc_.theta>1e-3 && rusdmc_.theta*180.0/M_PI < atof(cmd_opt.get("thetaminmc").c_str())) return;
  if(cmd_opt.isset("thetamaxmc") && rusdmc_.theta>1e-3 && rusdmc_.theta*180.0/M_PI > atof(cmd_opt.get("thetamaxmc").c_str())) return;

  if(cmd_opt.isset("rlost") && rusdraw_.event_code == 0) {
    bool islost= (rusdgeom_.theta[0]<1e-10 && rusdgeom_.phi[0]<1e-10);
    double mindist_mc=mindist(rusdraw_.site, rusdmc_.corexyz[0]/1.0e5/1.2 - RUSDGEOM_ORIGIN_X_CLF,
			 rusdmc_.corexyz[1]/1.0e5/1.2 - RUSDGEOM_ORIGIN_Y_CLF);
    printf("%s %i %i %i"
	   " %lg %lg %lg %lg %lg %lg %lg\n",
	   islost?"LOST":"NOTL",
	   rusdmc_.event_num, rusdmc_.parttype, rusdmc_.corecounter, 
	   rusdmc_.energy, rusdmc_.theta*180.0/M_PI,
	   (tasdcalibev_.sim.primaryEnergy>1e-9)?tasdcalibev_.sim.primaryAzimuth:inv_phi(rusdmc_.phi*180.0/M_PI),
	   rusdmc_.height/1.0e5, rusdmc_.corexyz[0]/1.0e5,  rusdmc_.corexyz[1]/1.0e5,
	   1.2*mindist_mc
	     );   
    return;
  }

  if(rusdgeom_.theta[0]<1e-10 && rusdgeom_.phi[0]<1e-10 && !cmd_opt.isset("junk")) {
    return;
  }
  if((!tstBankList(sdrun.gotBanks,RUSDRAW_BANKID) || !tstBankList(sdrun.gotBanks,RUSDGEOM_BANKID)) && !cmd_opt.isset("junk")) {
    return;
  }
  fiteta = false; // to avoid error when calling s_eta    

  double mindist_ru = mindist(rusdraw_.site, rusdgeom_.xcore[anal], rusdgeom_.ycore[anal]);

  double theta,phi;
  theta = rusdgeom_.theta[anal]/(180.0/M_PI);
  phi = rusdgeom_.phi[anal]/(180/M_PI);
  int cnt = 0;
  double s_s_pfs=0; // Sum (signal_i*profile_i)/error_i^2
  double s_s_pps=0; // Sum (profile_i*profile_i)/error_i^2

  ev = rusdraw_.yymmdd*1000ll*1000ll*10ll + rusdraw_.hhmmss*10ll + rusdraw_.site;

  int second_count=0;

  for(int sd=0;sd < rusdgeom_.nsds; sd++) {
    if(rusdgeom_.xxyy[sd]==rusdmc_.corecounter) {
      corecounterX = 1.2*(rusdgeom_.xyzclf[sd][0]);
      corecounterY = 1.2*(rusdgeom_.xyzclf[sd][1]);
    }

    double x,y,z,r_plane,r;
    x = rusdgeom_.xyzclf[sd][0]-(rusdgeom_.xcore[anal]+RUSDGEOM_ORIGIN_X_CLF);
    y = rusdgeom_.xyzclf[sd][1]-(rusdgeom_.ycore[anal]+RUSDGEOM_ORIGIN_Y_CLF);
    z = rusdgeom_.xyzclf[sd][2];
    r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
    r = sqrt(x*x+y*y+z*z-r_plane*r_plane);

    if(cmd_opt.isset("v")) {
      printf("  SD %i, detector: %i signals: %i, VEM: %lg, isgd: %i time: %.9lf"
	     "\n\txyzr: %lg %lg %lg %lg\n", sd, rusdgeom_.xxyy[sd], rusdgeom_.nsig[sd],
	     rusdgeom_.pulsa[sd], rusdgeom_.igsd[sd], rusdgeom_.sdtime[sd]/RUFPTN_TIMDIST*1e-6,
	     x,y,z,r);
      double sig=0.0;
      for(int h=0; h < rufptn_.nhits; h++) {
	if( rufptn_.xxyy[h] != rusdgeom_.xxyy[sd] || rufptn_.isgood[h]<4) continue;
	for(int wf = rufptn_.wfindex[h];wf<rufptn_.wfindex[h]+rufptn_.nfold[h]; wf++) {
	  for(int c2=0;c2<rusdraw_nchan_sd;c2++) {
	    if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][0] ) &&
		 ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][0]) ) {
	      sig += 1.22*0.5*(double(rusdraw_.fadc[wf][0][c2])- double(rusdraw_.pchped[wf][0])/8.0)/rusdraw_.mip[wf][0];
	    }
	    if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][1] ) &&
		 ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][1]) ) {
	      sig += 1.22*0.5*(double(rusdraw_.fadc[wf][1][c2])- double(rusdraw_.pchped[wf][1])/8.0)/rusdraw_.mip[wf][1];
	    }
	  }
	  printf("\twf_id: %i, xxyy: %i, time: %.9f", rusdraw_.wf_id[wf], rusdraw_.xxyy[wf], 
		 double(rusdraw_.clkcnt[wf])/double(rusdraw_.mclkcnt[wf])-(rusdgeom_.tearliest - int(rusdgeom_.tearliest)));
        }
      }
      if(sig>0) printf("\tVEM: %g\n", sig);
    }


    if(rusdgeom_.igsd[sd]>=2 || rusdgeom_.pulsa[sd] > 10) {

      double s_result = rusdgeom_.pulsa[sd] / DET_AREA;
      double s_prof = s_profile(r, theta, s_eta(theta), r_plane);
      double s_error = sqrt(s_profile(r, theta, s_eta(theta), r_plane));
      if((r>s_RMINCUT)&&(r<s_RMAXCUT)) {    
	s_s_pfs += s_result*s_prof/s_error/s_error;
	s_s_pps += s_prof*s_prof/s_error/s_error;
      }

      cnt++;

	
      int after=0, dbl=0;
      if(rusdgeom_.nsig[sd]>=2) {
	for(int sig=0;sig<rusdgeom_.nsig[sd];sig++) {
	  if(cmd_opt.isset("v")) {
	    printf("\t\tSignal: %i, good: %i, rufptn: %i VEM: %lg time: %.9lf\n", sig, rusdgeom_.igsig[sd][sig],
		   rusdgeom_.irufptn[sd][sig], rusdgeom_.sdsigq[sd][sig],
		   rusdgeom_.sdsigt[sd][sig]/RUFPTN_TIMDIST*1e-6);
	  }
	  if(after && rusdgeom_.igsig[sd][sig]) {
	    dbl = 1;
	  }
	  if(rusdgeom_.igsig[sd][sig]>=4) {
	    after = 1;
	  }
	}
      }
      second_count+=dbl;
    }
  }

  double S_X = (s_s_pps>1e-10)?(s_s_pfs/s_s_pps):1;

  dcount = 0; 
  dcount_nz = 0; // non-zero counters
  dcount_ng = 0; // no geometry counters
  int satur_count=0; // saturated counters
  gl_pcnt = 0; gl_pcnt_largest =0; gl_largest_xxyy = 0; gl_apcnt_u = 0; gl_apcnt_l = 0;
  gl_ul_diff = 0.0; gl_ul_sum = 0.0; gl_largest_signal = 0.0;


  double t0 = 0.0, max_signal_tf=0.0, max_signal=0, tot_signal=0;
  for(int sd=0;sd < rusdgeom_.nsds; sd++) {
    if( rusdgeom_.igsd[sd]>=2
	|| (!cmd_opt.isset("nobaddet") && (rusdgeom_.pulsa[sd] > 10 || cmd_opt.isset("baddet"))) ) {
      // We keep large signal bad timing counters for LDF fit only
      bool calibev_bad=0;
      int satur_upper=0, satur_lower=0;
      float clockError;
      for(int cx=0;cx<tasdcalibev_.numWf;cx++) {
	if( tasdcalibev_.sub[cx].lid==rusdgeom_.xxyy[sd]){
	  if(tasdcalibev_.sub[cx].wfError & 64) {// DAQ error (FPGA to SDRAM)
	    calibev_bad=1;
	  }
	  if(cmd_opt.isset("dontuse")) {
	    if(tasdcalibev_.sub[cx].dontUse) {
	      printf("Don't use: %i, reason: %i\n", rusdgeom_.xxyy[sd], tasdcalibev_.sub[cx].dontUse);
	      calibev_bad=1;
	    }
	    if(tasdcalibev_.sub[cx].wfError) {
	      satur_upper |= (tasdcalibev_.sub[cx].wfError & 21);
	      satur_lower |= (tasdcalibev_.sub[cx].wfError & 42);
	      printf("Wf error of saturation: %i, reason: 0x%x\n", rusdgeom_.xxyy[sd], tasdcalibev_.sub[cx].wfError);
	      if(tasdcalibev_.sub[cx].wfError & 64) {
		printf("\tDAQ error (FPGA to SDRAM)\n");
		calibev_bad=1;
	      }
	    }
	    if(tasdcalibev_.sub[cx].warning) {
	      printf("Warning: %i, reason: 0x%x\n", rusdgeom_.xxyy[sd], tasdcalibev_.sub[cx].warning);
	    }
	    clockError = tasdcalibev_.sub[cx].clockError;
	    //	    printf("DEBUG %g %g %g %g\n", tasdcalibev_.sub[cx].clockError, tasdcalibev_.sub[cx].upedAvr, tasdcalibev_.sub[cx].upedStdev, tasdcalibev_.sub[cx].umipMev2cnt);
	  }
	}
      }
      if(cmd_opt.isset("dontuse")) {
	int satur_rutgers = (rusdgeom_.igsd[sd]==3)?1:0;
	if(satur_rutgers || satur_upper || satur_lower) {
	  printf("SATUR %i %i %i %g %i\n", (rusdgeom_.igsd[sd]>=2)?satur_rutgers:-1, satur_upper, satur_lower, clockError, calibev_bad);
	}
      }
      if(calibev_bad) continue; // generally check for DAQ error only, if dontuse option enabled, check also for .dontUse option

      double x,y,z,r,r_plane;
      x = rusdgeom_.xyzclf[sd][0]-(rusdgeom_.xcore[anal]+RUSDGEOM_ORIGIN_X_CLF);
      y = rusdgeom_.xyzclf[sd][1]-(rusdgeom_.ycore[anal]+RUSDGEOM_ORIGIN_Y_CLF);
      z = rusdgeom_.xyzclf[sd][2];
      r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
      r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
      if(!cmd_opt.isset("baddet") && 
	 ( rusdgeom_.igsd[sd]==0 || (rusdgeom_.igsd[sd]==1 && sqrt(x*x+y*y+z*z)>2) )) {
	continue; // igsd=0 is bad; igsd=1 far away detector is probably not good
      }

      double sig=0.0, tsig=0.0;
      double tX = -1.0;
      if(cmd_opt.isset("median") || cmd_opt.isset("weight")) {
	for(int h=0; h < rufptn_.nhits; h++) {
	  if( rufptn_.xxyy[h] != rusdgeom_.xxyy[sd] || rufptn_.isgood[h]<3) continue;
	  for(int wf = rufptn_.wfindex[h];wf<rufptn_.wfindex[h]+rufptn_.nfold[h]; wf++) {
	    for(int c2=0;c2<rusdraw_nchan_sd;c2++) {
	      double x=0.0;
	      if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][0] ) &&
		   ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][0]) ) {
		x += 1.22*0.5*(double(rusdraw_.fadc[wf][0][c2])- double(rusdraw_.pchped[wf][0])/8.0)/rusdraw_.mip[wf][0];
	      }
	      if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][1] ) &&
		   ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][1]) ) {
		x += 1.22*0.5*(double(rusdraw_.fadc[wf][1][c2])- double(rusdraw_.pchped[wf][1])/8.0)/rusdraw_.mip[wf][1];
	      }
	      sig += x;
	      tsig += x*(double(rusdraw_.clkcnt[wf])/double(rusdraw_.mclkcnt[wf])-(rusdgeom_.tearliest - int(rusdgeom_.tearliest))
			 + double(c2)*20e-9);
	    }
	  }
	}
    	 
	double sig2=0.0;
	for(int h=0; h < rufptn_.nhits; h++) {
	  if( rufptn_.xxyy[h] != rusdgeom_.xxyy[sd] || rufptn_.isgood[h]<3) continue;
	  for(int wf = rufptn_.wfindex[h];wf<rufptn_.wfindex[h]+rufptn_.nfold[h]; wf++) {
	    for(int c2=0;c2<rusdraw_nchan_sd;c2++) {
	      if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][0] ) &&
		   ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][0]) ) {
		sig2 += 1.22*0.5*(double(rusdraw_.fadc[wf][0][c2])- double(rusdraw_.pchped[wf][0])/8.0)/rusdraw_.mip[wf][0];
	      }
	      if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][1] ) &&
		   ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][1]) ) {
		sig2 += 1.22*0.5*(double(rusdraw_.fadc[wf][1][c2])- double(rusdraw_.pchped[wf][1])/8.0)/rusdraw_.mip[wf][1];
	      }
	      if(sig2 > 0.5*sig) {
		tX = double(rusdraw_.clkcnt[wf])/double(rusdraw_.mclkcnt[wf])-(rusdgeom_.tearliest - int(rusdgeom_.tearliest))
		  + double(c2)*20e-9;
		if(cmd_opt.isset("v")) {
		  printf(" %i tX: %.9f  t0: %.9f  tW: %.9f\n", rusdgeom_.xxyy[sd], tX, rusdgeom_.sdtime[sd]/RUFPTN_TIMDIST*1e-6, tsig/sig);
		}
		break;
	      }
	    }
	    if(tX>0) break;
	  }
	  if(tX>0) break;
	}
      }

      dsaturated[dcount] =  ((rusdgeom_.igsd[sd]==3)?1:0);
      if(rusdgeom_.igsd[sd]==1 && rusdgeom_.pulsa[sd]/DET_AREA > 15) {
	dsaturated[dcount] = 1;
	// this is to account manually detectors with igsd=1
      }

      dvalue[dcount][4] = rusdgeom_.sdtime[sd];
      dvalue[dcount][7] = (rusdgeom_.igsd[sd]<2)?1:0;

      if(cmd_opt.isset("c500")) { // mark detectors within 500 m as saturated for Taketa's MC
	  double m_x = rusdgeom_.xyzclf[sd][0]-rusdmc_.corexyz[0]/1.0e5/1.2;
	  double m_y = rusdgeom_.xyzclf[sd][1]-rusdmc_.corexyz[1]/1.0e5/1.2;
	  double m_z = rusdgeom_.xyzclf[sd][2]-rusdmc_.corexyz[2]/1.0e5/1.2;
	  double m_ctheta = tasdcalibev_.sim.primaryCosZenith;
	  double m_phi = tasdcalibev_.sim.primaryAzimuth/180.0*M_PI;
	  double m_r_plane = sqrt(1-m_ctheta*m_ctheta)*(cos(m_phi)*m_x + sin(m_phi)*m_y) - m_ctheta*m_z;
	  double m_r = sqrt(m_x*m_x+m_y*m_y+m_z*m_z-m_r_plane*m_r_plane);
	  if(m_r<500.0/1200.0) {
	    continue;
	  }
      }

      int pcnt = 0, apcnt_u = 0, apcnt_l = 0;
      double ul_diff = 0.0, ul_sum = 0.0, ul_asymm = 0.0;
      double ul_MIN = 0.2;
      double PeakVal=0.0;
      for(int h=0; h<rufptn_.nhits; h++) {
	if( rufptn_.xxyy[h] != rusdgeom_.xxyy[sd]) continue;
	if( !cmd_opt.isset("baddet") && rufptn_.isgood[h]<3 ) continue;
	for(int wf = rufptn_.wfindex[h];wf<rufptn_.wfindex[h]+rufptn_.nfold[h]; wf++) {
	  for(int c2=0;c2<rusdraw_nchan_sd;c2++) {
	    double w[2] = {0,0};
	    int ispeak = 0;
	    for(int layer=0; layer<=1; layer++) {
	      if ( ( wf >  rufptn_.wfindex[h] || c2 >= rufptn_.sstart[h][layer] ) &&
		   ( wf<rufptn_.wfindex[h]+rufptn_.nfold[h] - 1  || c2 <= rufptn_.sstop[h][layer]) ) {
		w[layer] += 1.22*(double(rusdraw_.fadc[wf][layer][c2])- double(rusdraw_.pchped[wf][layer])/8.0)/rusdraw_.mip[wf][layer];
		if(c2>=3 && c2<rusdraw_nchan_sd-3) {
		  if(w[layer] > ul_MIN 
		     && rusdraw_.fadc[wf][layer][c2] > rusdraw_.fadc[wf][layer][c2+1] && rusdraw_.fadc[wf][layer][c2] > rusdraw_.fadc[wf][layer][c2-1]
		     && rusdraw_.fadc[wf][layer][c2] > rusdraw_.fadc[wf][layer][c2+2] && rusdraw_.fadc[wf][layer][c2] > rusdraw_.fadc[wf][layer][c2-2]
		     && rusdraw_.fadc[wf][layer][c2] > rusdraw_.fadc[wf][layer][c2+3] && rusdraw_.fadc[wf][layer][c2] > rusdraw_.fadc[wf][layer][c2-3]) {
		    pcnt++;
		    ispeak++;
		  }
		}
	      }
	    }
	    if((w[0] + w[1])/2. > PeakVal) {
	      PeakVal = (w[0] + w[1])/2.;
	    }
	    if(w[0] + w[1] > sqrt(2.0)*ul_MIN) {
	      if(ispeak) {
		if( w[1] - w[0] > 1/3.0*(w[0] + w[1])) {
		  apcnt_u++;
		}
		if( w[1] - w[0] < -1/3.0*(w[0] + w[1])) {
		  apcnt_l++; // lower asymmetric peak
		}
	      }
	      ul_diff += fabs(w[1] - w[0]);
	      ul_sum += fabs(w[1] + w[0]);
	    }
	  }
	}
      }
      if(ul_sum>0.1) {
	ul_asymm = ul_diff / ul_sum;
      }
      if(!dsaturated[dcount]) {
	if(rusdgeom_.pulsa[sd] > gl_largest_signal) {
	  gl_pcnt_largest = pcnt;
	  gl_largest_xxyy = rusdgeom_.xxyy[sd];
	  gl_largest_signal = rusdgeom_.pulsa[sd];
	}
	gl_pcnt+=pcnt;
	gl_apcnt_u+=apcnt_u;
	gl_apcnt_l+=apcnt_l;
	gl_ul_diff += ul_diff;
	gl_ul_sum += ul_sum;
      }
      dvalue[dcount][8] = pcnt;
      dvalue[dcount][9] = ul_asymm;
      dvalue[dcount][10] = PeakVal/DET_AREA;
      //      }

      if(cmd_opt.isset("median")) {
	if(tX<0 || dsaturated[dcount]) { // saturated detectors spoil median
	  dvalue[dcount][7] = 1;
	}
	else {
	  dvalue[dcount][4] = (tX*RUFPTN_TIMDIST)/1e-6;
	}
      }       	
      else if(cmd_opt.isset("weight")) {
	if(sig<1e-10) {
	  dvalue[dcount][7] = 1;
	}
	else{
	  dvalue[dcount][4] = tsig/sig*RUFPTN_TIMDIST/1e-6;
	}
      }

      dvalue[dcount][0] = x;
      dvalue[dcount][1] = y;
      dvalue[dcount][2] = z;
      dvalue[dcount][3] = rusdgeom_.pulsa[sd]/DET_AREA;
      dxxyy[dcount] = rusdgeom_.xxyy[sd];

      tot_signal += rusdgeom_.pulsa[sd];
      if(!dvalue[dcount][7] && rusdgeom_.pulsa[sd] > max_signal_tf) {
	t0 = dvalue[dcount][4] - r_plane; // t0 is determined from non geomexcluded detectors
	max_signal_tf = rusdgeom_.pulsa[sd];
      }
      if(rusdgeom_.pulsa[sd] > max_signal) {
	max_signal = rusdgeom_.pulsa[sd];
      }
      satur_count += dsaturated[dcount];
      if(dvalue[dcount][7]) {
	dcount_ng++;
      }
      dcount++;
      dcount_nz++;
    }
  }
  
  if(cmd_opt.isset("ndet")) {
    if(dcount_nz < atoi(cmd_opt.get("ndet").c_str())) return;
  }

  load_zero(3.5);

  double init[8], step[8];

  int params_num;

  if(cmd_opt.isset("fiteta")) {
    params_num = 8;
    init[7] = s_eta(theta);
    step[7] = 0.2;
    fiteta = true;
  }
  else {
    params_num = 7;
  }


  // 0 - xcore, 1 - ycore, 2 - theta, 3 - phi, 4 - t0, 5 - log(S600), 6 - curvature
  double aprime, a_ivanov;
  double P;

  init[0] = init[1] = 0.0;
  init[2] = theta; init[3] = phi;
  init[4] = t0;
  init[5] = log(S_X);
  if(theta < 25.0*DEG) {
    a_ivanov = 3.3836 - 0.01848*theta/DEG;
  }
  else if( theta < 35.0*DEG) {
    a_ivanov = (0.6511268210e-4*(theta/DEG-.2614963683))*(theta/DEG*theta/DEG-134.7902422*theta/DEG+4558.524091);
  }
  else {
    a_ivanov = exp(-3.2e-2*theta/DEG + 2.0);
  }
  
  init[6] = a_ivanov*1.3/sqrt(S_X);
  // looks like a_ivanov*1.3 is a good initial guess
  // this is essential for fits with fixed curvature (ndet=3,4)

  step[0] = step[1] = 0.3;
  step[2] = step[3] = 2*M_PI/180.0;
  step[4] = 0.4;
  step[5] = 0.2;
  step[6] = (dcount_nz>4)?0.3:0.0;
  
  if(cmd_opt.isset("v")) {
    printf("FITB: %lg %lg %lg %lg %lg %lg %lg %lli\n", init[0], init[1], init[2]*180/M_PI,
	   init[3]*180/M_PI, init[4], exp(init[5]), init[6], ev);
  }	

  calc_errorbars(init);
  P = do_fit(params_num, init, step, f_chi2, 100);
  
  if(cmd_opt.isset("v")) {
    printf("FITA0: %lg %lg %lg %lg %lg %lg %lg chi2/N=%lg Ndet=%i\n",
	   init[0], init[1], init[2]*180/M_PI, init[3]*180/M_PI, init[4],
	   exp(init[5]), init[6], P, dcount+dcount_nz);
  }
 

  calc_errorbars(init);
  P = do_fit(params_num, init, step, f_chi2, 200);

  if(cmd_opt.isset("v")) {
    printf("FITA1: %lg %lg %lg %lg %lg %lg %lg chi2/N=%lg Ndet=%i\n",
	   init[0], init[1], init[2]*180/M_PI, init[3]*180/M_PI, init[4],
	   exp(init[5]), init[6], P, dcount+dcount_nz);
  }	

  calc_errorbars(init);
  P = do_fit(params_num, init, step, f_chi2, 500);

  double P1 = 0.0;
  if(cmd_opt.isset("geom") && dcount_nz>=5) {
    calc_errorbars(init);
    step[0] = step[1] = step[5] = step[7] = 0.0; // fix core and S800
    fitgeom = true;
    P1 = do_fit(params_num, init, step, f_chi2, 200);
    P = fmax(P, P1);
  }

  fitgeom = false;


  if(cmd_opt.isset("v")) {
    printf("FITA2: %lg %lg %lg %lg %lg %lg %lg chi2/N=%lg Ndet=%i\n",
	   init[0], init[1], init[2]*180/M_PI, init[3]*180/M_PI, init[4],
	   exp(init[5]), init[6], P, dcount+dcount_nz);
  }	

  aprime = init[6];

  int y,m,d,h,mm,ss;
  y = rusdraw_.yymmdd/10000;
  m = (rusdraw_.yymmdd%10000)/100;
  d = rusdraw_.yymmdd%100;
  h = rusdraw_.hhmmss/10000;
  mm = (rusdraw_.hhmmss%10000)/100;
  ss = rusdraw_.hhmmss%100;
  double mytheta = init[2]*180/M_PI;
  double myphi = init[3]*180/M_PI;
  if(mytheta<0) {
    mytheta *= -1.0;
    myphi += 180.0;
  }
  if(mytheta>90) {
    mytheta = 180 - mytheta;
  }
  while(myphi>360) { myphi-=360.0;}
  while(myphi<0) { myphi+=360.0; }

  double E = estimatedE(exp(init[5]), mytheta);

  double mindist_gri=mindist(rusdraw_.site, rusdgeom_.xcore[anal] + init[0], rusdgeom_.ycore[anal] + init[1]);
  
  S_X = exp(init[5]);

  AOPcnt=0;
  for(int c1=0;c1<Sbcount;c1++) {
    Sb[c1]=0;
  }
  for(int c1=0; c1<dcount; c1++) {
    double x,y,z,r_plane,r;
    double theta = init[2];	 double phi   = init[3];
    x = dvalue[c1][0]-init[0];  y = dvalue[c1][1]-init[1];
    z = dvalue[c1][2];
    r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
    r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
    if(!dsaturated[c1] && ( dvalue[c1][7] < 0.5 )) {
      for(int c2=0;c2<Sbcount;c2++) {
	Sb[c2]+= dvalue[c1][3]*pow(r,Sb_b(c2));
      }
    }
    if(!dsaturated[c1] && ( dvalue[c1][7] < 0.5 ) && dvalue[c1][3]>0.1 && r>0.5 ) {
      AOPfitX[AOPcnt]=r;
      AOPfitY[AOPcnt]=dvalue[c1][3]/dvalue[c1][10]*20.;
      AOPfitW[AOPcnt]=1;
      AOPcnt++;
    }
  }
  //  gsl_fit_wlinear(AOPfitX, 1, AOPfitW, 1, AOPfitY, 1, AOPcnt, &AOPc0, &AOPc1, &AOPcov00, &AOPcov01, &AOPcov11, &AOPchi2);
  gsl_fit_linear(AOPfitX, 1, AOPfitY, 1, AOPcnt, &AOPc0, &AOPc1, &AOPcov00, &AOPcov01, &AOPcov11, &AOPchi2);
  gsl_fit_linear_est (1.0, AOPc0, AOPc1, AOPcov00, AOPcov01, AOPcov11, &AOP1200, &AOP1200_err);

  if(cmd_opt.isset("sdii")) {
     printf("SDII %s%i %i %i %i %i %i %i %i %i %g %g %g %g %g %g %g %g %g %g %g %g %g %i %i %i %i %g %g %g",
	   ((y<10)?"0":""),
	    y, m, d, h, mm, ss, rusdraw_.site,
	    dcount_nz, rufptn_.nborder,
	    (P>-0.1)?E:-1.0, (P>-0.1)?exp(init[5]):-1.0,
	    inv_phi(rusdgeom_.phi[anal]), rusdgeom_.dphi[anal],
	    rusdgeom_.theta[anal], rusdgeom_.dtheta[anal],
	    (P>-0.1)?mytheta:-1.0, (P>-0.1)?inv_phi(myphi):-1.0,
	    rusdgeom_.chi2[anal], P, (P>-0.1)?aprime*sqrt(S_X):-1.0, mindist_ru,
	    (P>-0.1)?mindist_gri:-1.0, satur_count, second_count, dcount - dcount_nz,
	    rusdraw_.usec,
	    rusdgeom_.xcore[anal] + RUSDGEOM_ORIGIN_X_CLF + init[0],
	    rusdgeom_.ycore[anal] + RUSDGEOM_ORIGIN_Y_CLF + init[1],
	    (P>-0.1)?S_X:-1.0);
    if(rusdraw_.event_code == 0) {
      printf(" %g %g %g",  rusdmc_.energy, rusdmc_.theta*180.0/M_PI,
	     (tasdcalibev_.sim.primaryEnergy>1e-9)?tasdcalibev_.sim.primaryAzimuth:inv_phi(rusdmc_.phi*180.0/M_PI));
    }
    printf(" %g %i %i %g %g %i %i %i %i", fit_final_size, dcount_ng, gl_pcnt,
	   0.5*gl_ul_sum, (gl_ul_sum>0?gl_ul_diff/gl_ul_sum:0.0),
	   gl_pcnt_largest, gl_largest_xxyy, gl_apcnt_u, gl_apcnt_l);
    printf(" %lg %lg %i", AOP1200, AOPc1, AOPcnt);
    for(int c1=0;c1<Sbcount;c1++) {
      printf(" %lg",Sb[c1]);
    }
    if(rusdraw_.event_code == 0) {
      printf(" %g",  rusdmc_.height/1e5);
    }
    printf("\n");
  }

  int db_date = (2000+y)*10000 + m*100 + d;
  double db_time = h*10000.0 + mm*100.0 + ss + rusdraw_.usec*1e-6;
  double db_xcore_gri = (P>-0.1)?(1.2*( rusdgeom_.xcore[anal] + RUSDGEOM_ORIGIN_X_CLF + init[0])):-1.0;
  double db_ycore_gri = (P>-0.1)?(1.2*( rusdgeom_.ycore[anal] + RUSDGEOM_ORIGIN_Y_CLF + init[1])):-1.0;
  double db_S800_gri = (P>-0.1)?S_X:-1.0;
  double db_theta_gri = (P>-0.1)?mytheta:-1.0;
  double db_phi_gri = (P>-0.1)?inv_phi(myphi):-1.0;
  double db_E_gri = (P>-0.1)?E/1e18:-1.0;
  double db_mindist_gri = (P>-0.1)?1.2*mindist_gri:-1.0;

  double eta = fiteta?init[7]:s_eta(init[2]);

  if(cmd_opt.isset("tstalive") && (dcount==dcount_nz || tasdcalibev_.numAlive==0)) {
    /* To search for events with incomplete information about alive detectors*/
    printf("Alive: %i %.6f %i %i %i\n", db_date, db_time, dcount_nz, dcount - dcount_nz, tasdcalibev_.numAlive);
  }

  printf("SDDB %i %.6f %lg %lg %lg %lg %lg 0 0 %lg" // Wiki
	 " %i %i %i %i %i %i %lg %lg %i %lg %lg %lg %lg %lg %i" // numbers and P,eta,fiteta,a,max_signal,tot_signal, mindist
	 " %i %g %g %i %i %i %i %g %g %i", // peak count, 0.5*ul_sum, asymmetry
	 db_date, db_time, db_xcore_gri, db_ycore_gri, db_S800_gri, db_theta_gri, db_phi_gri, db_E_gri,
	 rusdraw_.site, dcount_nz, rufptn_.nborder, satur_count, second_count, dcount - dcount_nz,
	 P, eta, fiteta, aprime*sqrt(S_X), max_signal, tot_signal, db_mindist_gri, fit_final_size, dcount_ng,
	 gl_pcnt, 0.5*gl_ul_sum, (gl_ul_sum>0?gl_ul_diff/gl_ul_sum:0.0), gl_pcnt_largest, gl_largest_xxyy,
	 gl_apcnt_u, gl_apcnt_l, AOP1200, AOPc1, AOPcnt);
  for(int c1=0;c1<Sbcount;c1++) {
    printf(" %g",Sb[c1]);
  }

  if(cmd_opt.isset("tstchi2")) {
    printf(" %lg %lg %lg %lg %lg %lg %lg %lg %lg %lg",
	   g_chi2L1, g_NL1, g_chi2L2, g_NL2, g_chi2L3, g_NL3, g_chi2Z, g_NZ, g_chi2T, g_NT);
  }
  if(rusdraw_.event_code != 0) {     
    printf("\n");
  }
  else {

    double mindist_mc=mindist(rusdraw_.site, rusdmc_.corexyz[0]/1.0e5/1.2 - RUSDGEOM_ORIGIN_X_CLF,
			      rusdmc_.corexyz[1]/1.0e5/1.2 - RUSDGEOM_ORIGIN_Y_CLF);

    printf(" %i %i %i"
	   " %lg %lg %lg %lg %lg %lg %lg\n",
	   rusdmc_.event_num, rusdmc_.parttype, rusdmc_.corecounter, 
	   rusdmc_.energy, rusdmc_.theta*180.0/M_PI,
	   (tasdcalibev_.sim.primaryEnergy>1e-9)?tasdcalibev_.sim.primaryAzimuth:inv_phi(rusdmc_.phi*180.0/M_PI),
	   rusdmc_.height/1.0e5, rusdmc_.corexyz[0]/1.0e5,  rusdmc_.corexyz[1]/1.0e5,
	   1.2*mindist_mc
	   );
  }

  if(cmd_opt.isset("sign")) {
    read_signals(init, db_date, db_time);
  }

  if(cmd_opt.isset("dtf")) {
    plot_dtf(init, P);
  }

  if(cmd_opt.isset("mcdt")) {
    if(rusdraw_.event_code == 0 && (P>-0.1) && (P<5.0) && (db_mindist_gri>0) && (S_X > 0.1) ) {     
      for(int sd=0;sd < rusdgeom_.nsds; sd++) {
	if(rusdgeom_.igsd[sd]>=2) {
	  double db_xcore_mc = rusdmc_.corexyz[0]/1.0e5;
	  double db_ycore_mc =  rusdmc_.corexyz[1]/1.0e5;
	  double x,y,z,r,r_plane;

	  x = rusdgeom_.xyzclf[sd][0]-db_xcore_mc/1.2;
	  y = rusdgeom_.xyzclf[sd][1]-db_ycore_mc/1.2;
	  z = rusdgeom_.xyzclf[sd][2];
	  theta = rusdmc_.theta;
	  phi = rusdmc_.phi;
	  r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
	  r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
	  double S = S_X*s_profile(r, theta, eta, r_plane);
	  printf("SDMCDT %lg %lg %lg %lg %lg %lg\n",
		 rusdmc_.energy, rusdmc_.theta*180.0/M_PI, r*1.2,
		 rusdgeom_.pulsa[sd]/DET_AREA, S, S_X);
	}
      }
    }
  }
  
  if(cmd_opt.isset("t")) {
    //    exit(1);
  }
}


#define R_error 0.125

void calc_errorbars(double *init) {
  double S_X = exp(init[5]);
  double aprime = init[6];
  double theta = init[2];
  double phi = init[3];
  double eta = fiteta?init[7]:s_eta(theta);

  for(int c1=0; c1<dcount; c1++) {
    double x, y, z, S, r_plane, r, t_s, r_c;
    x = dvalue[c1][0] - init[0];
    y = dvalue[c1][1] - init[1];
    z = dvalue[c1][2];
    S = dvalue[c1][3];
    r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
    r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
    r_c = (r > R_error)?r:R_error; // for front error calculation we should consider possible core distance error
    t_s = (aprime*sqrt(S_X))*linsley_s(r_c, S_X*s_profile(r_c, theta, eta, r_plane));
    dvalue[c1][5] = RMS_S(S, DET_AREA);
    dvalue[c1][6] = (30*NSEC)*(30*NSEC) + t_s*t_s;
  }
  return;
}

double f_chi2(const gsl_vector *v, void *d) {
  double xcore = gsl_vector_get(v, 0);
  double ycore = gsl_vector_get(v, 1);
  double theta = gsl_vector_get(v, 2);
  double phi   = gsl_vector_get(v, 3);
  double eta = fiteta?gsl_vector_get(v,7):s_eta(theta);
  double t0 = gsl_vector_get(v, 4);
  double S_X = exp(gsl_vector_get(v, 5));
  double aprime = gsl_vector_get(v, 6);

  g_chi2L1=0.0; g_chi2L2=0.0; g_chi2L3 = 0.0; g_chi2Z=0.0; g_chi2T=0.0;
  g_NL1=0.0; g_NL2 = 0.0; g_NL3 = 0.0; g_NZ=0.0; g_NT=0.0;

  for(int c1=0; c1<dcount; c1++) {
    double x, y, z, S, t, r_plane, r, s_fit, t_d, t_sigma2, s_sigma2;
    x = dvalue[c1][0]-xcore;
    y = dvalue[c1][1]-ycore;
    z = dvalue[c1][2];
    S = dvalue[c1][3];
    t = dvalue[c1][4];
    r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
    r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
    double s_prof = s_profile(r, theta, eta, r_plane);
    s_fit = S_X*s_prof;

    t_d = aprime*linsley_t(r, s_prof);

    s_sigma2 = dvalue[c1][5];
    t_sigma2 = dvalue[c1][6];
    
    if(isnan(s_fit)) {
      printf("D7 %g %g %g %g %g\n", S_X, r, theta, eta, r_plane);
    }
    
    if(S>0.1) {
      if(!dvalue[c1][7]) {
	g_chi2T += (t0 + r_plane + t_d - t)*(t0 + r_plane + t_d - t)/t_sigma2;
	g_NT++;
      }
      if(dsaturated[c1]) {
	if(cmd_opt.isset("desaturate")) {
	  double x = desaturate(S);
	  g_chi2L1 += 0.25*(x - s_fit)*(x - s_fit)/s_sigma2;
	  g_NL1+=0.4;
	}
	/*	else {
	  if( S > s_fit ) {
	    g_chi2L1 += (S - s_fit)*(S - s_fit)/s_sigma2;
	  }
	  else {
	    g_chi2L1 += 0.0;
	  }
	}*/
      }
      else {
	if(s_fit > 4.0) {
	  g_chi2L2 += (S - s_fit)*(S - s_fit)/s_sigma2;
	  g_NL2++;
	}
	else {
	  g_chi2L3 -= 0.4*logPua(S*DET_AREA, s_fit*DET_AREA); 
	  g_NL3++;
	}
      }
    }
    else {
      g_chi2Z -= 0.25*logPua(0, s_fit*DET_AREA);  // 0.7
      // I expect that error is larger than Poisson, but coefficient is arbitrary
      g_NZ += 0.1; //0.1;
    }
  }

  double chi2,N, nfree;
  if(!fitgeom) { // joint fit
    chi2=g_chi2L1 + g_chi2L2 + g_chi2L3 + g_chi2Z + g_chi2T;
    N=g_NL1 + g_NL2 + g_NL3 + g_NZ + g_NT;
    nfree = 7;
  }
  else { // geometry fit
    chi2 = g_chi2T;
    N = g_NT;
    nfree = 4;
  }
  //  if(isnan(chi2)) return 1e100;
  return (N>nfree)?(chi2/(N-nfree)):chi2;
}

double logPua(double n, double nbar) {
  if(nbar < 1e-90) {
    if(n<1e-90) {
      return 0;
    }
    else {
      //      fprintf(stderr, "logPua(), model inconsistent, nbar = %lg, n=%lg\n", nbar, n);
      //      exit(1);
      return -1e6;
    }
  }

  if(n < 1e-20) {
    return 2*(-nbar);
  }
  return 2*(n*log(nbar/n) + (n - nbar));
}

#define LINSLEY_r0 0.025 //0.025
double linsley_t(double r, double S) {
  //  return r*r/(2*5.0*5.0);
  return 0.67*pow((1 + r/LINSLEY_r0), 1.5)*pow(S, -0.5)*NSEC;
}

double linsley_s(double r, double S) {
  return 1.3*0.29*pow((1 + r/LINSLEY_r0), 1.5)*pow(S, -0.3)*NSEC;
}

double s_eta(double theta) {
  //  return 3.97 - 1.79*(1/cos(theta) - 1);
  if(fiteta) {
    fprintf(stderr, "BUG: fiteta is enabled but s_eta() called\n");
    exit(1);
  }

  double e;
  double x = theta*180.0/M_PI;

  if(x<62.7) { // AGASA formula up to 62.7 degrees
    e = 3.97 - 1.79*(fabs(1.0/cos(theta)) - 1.0);
  }
  else {
    e = ((((((-1.71299934e-10*x + 4.23849411e-08)*x -3.76192000e-06)*x
               + 1.35747298e-04)*x -2.18241567e-03)*x + 1.18960682e-02)*x
             + 3.70692527e+00);
  }
  return e;
}

double desaturate(double S) {
  return (S>200)?(exp(log(200)*(-0.7/0.3)+log(S)*1/0.3)):S;
}


double s_profile(double r_ta, double theta, double eta, double r_plane) {
  return s_profile_tasimple(r_ta, theta, eta)/s_profile_tasimple(r_X, theta, eta);
}

double s_profile_tasimple(double r_ta, double theta, double eta) {
  double r = r_ta*UNIT;
  double Rm = 90e2;
  double R1 = 1000.0e2;
  return (pow((r/Rm),-1.2)*pow((1+r/Rm), -(eta-1.2))*pow(1+(r*r/R1/R1),-0.6));
}

double attenuation(double theta) {
  return exp(-1.32589555e-07*(pow(theta,4.)-pow(28.65, 4.)));
}

double estimatedE(double S800,double theta) {
  if(!cmd_opt.isset("cosm")) {
    return 3.37e17*pow(S800/1.22/attenuation(theta), 1.12);
  }
  else {
    return 4.79e17*pow(S800/1.22/attenuation(theta), 1.03);
  }
}


double mindist(int site, double xcore, double ycore) {
  double t, b[2], bdist, tbr[2], tdistbr, tlr[2], tdistlr, tsk[2], tdistsk;
  sdbdist(xcore, ycore, b, &bdist, tbr, &tdistbr, tlr, &tdistlr, tsk, &tdistsk);

  switch(site) {
    case RUSDRAW_BR: t = tdistbr; break;
    case RUSDRAW_LR: t = tdistlr; break;
    case RUSDRAW_SK: t = tdistsk; break;
    case RUSDRAW_BRLR: t = -tdistsk; break;
    case RUSDRAW_BRSK: t = -tdistlr; break;
    case RUSDRAW_LRSK: t = -tdistbr; break;
    case RUSDRAW_BRLRSK: t = 1e10; break;
    default:
      fprintf(stderr, "Wrong tower: %i\n", rusdraw_.site);
      exit(1);
  }
  return (bdist<t)?bdist:t;
}

double RMS_S(double S, double area) { // S is density per m^2
  if(S<0.1) {
    return 1.0/(area*area);
  }	
  else {
    return 2*S/area + 0.15*0.15*S*S;
  }	
}

bool dtinfo_cmp(dtinfo a, dtinfo b) {
  return a.r_plane < b.r_plane;
}


void plot_dtf(double *init, double P) {
  FILE *fil, *gp1, *gp2, *gp3, *gp4, *gp5;
    char fname_base[sd_fname_size], fname[sd_fname_size], cmd[sd_fname_size];
    char gp_cmd1[gp_maxcmd], gp_cmd2[gp_maxcmd], gp_cmd3[gp_maxcmd], gp_cmd4[gp_maxcmd], gp_cmd5[gp_maxcmd], tmp_cmd[gp_maxcmd], title_cmd[gp_maxcmd];
    sprintf(fname_base, "%s%.6f", rusdraw_.yymmdd<1e5?"0":"",
	    rusdraw_.yymmdd+rusdraw_.hhmmss/1e6);
    sprintf(fname, "%s/%s.dtf", OUTDIR, fname_base);
    fil = fopen(fname, "wb");

    double xcore = init[0]; 	 double ycore = init[1];
    double theta = init[2];	 double phi   = init[3];
    double t0 = init[4];	 double S_X = exp(init[5]);
    double aprime = init[6];
    double eta = fiteta?init[7]:s_eta(theta);

    dtinfo dti[RUFPTNMH];

    gp_cmd3[0] = 0;
    double yymin = dvalue[0][1] + rusdgeom_.ycore[anal];
    double yymax = dvalue[0][1] + rusdgeom_.ycore[anal];
    
    for(int c1=0; c1<dcount; c1++) {
      yymin = fmin(yymin, dvalue[c1][1] + rusdgeom_.ycore[anal]);
      yymax = fmax(yymax, dvalue[c1][1] + rusdgeom_.ycore[anal]);
      double x,y,z,S,t, r_plane, r, s_fit, t_d, t_s, s_sigma;
      x = dvalue[c1][0]-xcore;  y = dvalue[c1][1]-ycore;
      z = dvalue[c1][2];  	S = dvalue[c1][3];
      t = dvalue[c1][4];
      int badgeom = int(dvalue[c1][7]);

      r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
      r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
      s_fit = S_X*s_profile(r, theta, eta, r_plane);

      dti[c1].xxyy = dxxyy[c1];
      dti[c1].r_plane = r_plane;
      dti[c1].r = r;
      dti[c1].zero = (S<0.1)?1:0;

      s_sigma = sqrt(dvalue[c1][5]);
      if(S<0.1) {
	S =0.01;
	s_sigma = sqrt(RMS_S(0, DET_AREA));
	t_d = 0;
	t_s = 0;
      }
      else {
	t_d = aprime*linsley_t(r, s_profile(r, theta, eta, r_plane));
	t_s = sqrt(dvalue[c1][6]);
      }

      fprintf(fil, "%.3lf %lg %lg %lg %lg %lg %lg %.10lg %.10lg %lg %i DTF %lli %lg %lg %i %i %lg %i %lg\n", r,
	      x+xcore+rusdgeom_.xcore[anal],
	      y+ycore+rusdgeom_.ycore[anal], r_plane,
	      S, s_fit, s_sigma, t, r_plane + t0 + t_d, t_s, dsaturated[c1], ev, theta*180.0/M_PI, S_X, badgeom, 
	      int(dvalue[c1][8]), dvalue[c1][9], dxxyy[c1], dvalue[c1][10]);
      if(S>0.1) {
	sprintf(tmp_cmd, "set label at %g,%g point lt %i pt 7 ps %g;",
		x+xcore+rusdgeom_.xcore[anal], y+ycore+rusdgeom_.ycore[anal],
		dsaturated[c1]?3:1, log(S+2)*2);
	strcat(gp_cmd3, tmp_cmd);
      }
    }
    fclose(fil);

    sprintf(fname, "%s/%s.dtfx", OUTDIR, fname_base);
    fil = fopen(fname, "wb");

    std::vector<dtinfo> dtvector(dti, dti+dcount);
    std::vector<dtinfo>::iterator dtit;
    sort(dtvector.begin(), dtvector.begin()+dcount, dtinfo_cmp);
    double yoffset = 0;

    for (dtit=dtvector.begin(); dtit!=dtvector.begin()+dcount; ++dtit) {
      if(dtit->zero) continue;
      //      std::cout << " " << dtit->r_plane << " " << dtit->xxyy << "\n";
      double ymax = 0;
      for(int h=0; h<rufptn_.nhits; h++) {
	if( rufptn_.xxyy[h] != dtit->xxyy || rufptn_.isgood[h]==0) continue;
       	if( !cmd_opt.isset("sign") && !cmd_opt.isset("baddet") && rufptn_.isgood[h]<3 ) continue;

	for(int layer=0; layer<=1; layer++) { // this cycle first makes correct point order for gnuplot
	  for(int wf = rufptn_.wfindex[h];wf<rufptn_.wfindex[h]+rufptn_.nfold[h]; wf++) {
	    for(int c2=0;c2<rusdraw_nchan_sd;c2++) {
	      double w[2] = {0,0};
	      double tX = (double(rusdraw_.clkcnt[wf])/double(rusdraw_.mclkcnt[wf])-(rusdgeom_.tearliest - int(rusdgeom_.tearliest)))*1e9
		+ double(c2)*20;
	      tX*=NSEC;
	      w[layer] = 1.22*(double(rusdraw_.fadc[wf][layer][c2])- double(rusdraw_.pchped[wf][layer])/8.0)/rusdraw_.mip[wf][layer];
	      if(w[layer]>ymax) ymax=w[layer];
	      fprintf(fil, "%i %i %.10g %g %g %g %g\n", dtit->xxyy, layer, tX, w[layer], yoffset, dtit->r_plane, dtit->r);
	    }	
	  }
	}
      }
      yoffset += ceil(ymax*1.05);
    }
    fclose(fil);

    if(cmd_opt.isset("gnu")) {
      sprintf(title_cmd, "set title \"%li %.6f (%.2f, %.2f) ndet=%i angles: %.1f, %.1f S800=%.3g a=%.3g eta=%.3g%s chi2/N=%.4g",
	      20000000l+rusdraw_.yymmdd, rusdraw_.hhmmss+1e-6*rusdraw_.usec,
	      xcore+rusdgeom_.xcore[anal], ycore+rusdgeom_.ycore[anal], dcount_nz,
	      init[2]*180.0/M_PI, inv_phi(init[3]*180.0/M_PI), exp(init[5]), aprime, eta, fiteta?"":"fix", P);

      if(rusdmc_.event_num) {
	sprintf(tmp_cmd, "\\n MC (%.2f, %.2f) angles: %.1f, %.1f E=%.3g\";", rusdmc_.corexyz[0]/1.0e5,
		rusdmc_.corexyz[1]/1.0e5, rusdmc_.theta*180.0/M_PI, inv_phi(rusdmc_.phi*180.0/M_PI),
		rusdmc_.energy);
      }
      else {
	sprintf(tmp_cmd, "\";");
      }
      strcat(title_cmd, tmp_cmd);


      sprintf(cmd, "cd %s; cat %s.dtf | sort -n > %s.tmp && mv %s.tmp %s.dtf", OUTDIR, fname_base, fname_base, fname_base, fname_base);    
      system(cmd);
      sprintf(gp_cmd1, "set logscale y; %s plot  \"%s.dtf\" u 1:6 title \"fit\" w l lt 2, \"%s.dtf\" u (($11==0)?$1:1/0):5:7 title \"data\" w e lt 1, \"%s.dtf\" u (($11>0)?$1:1/0):5:7 title \"saturated\" w e lt 3\n", title_cmd, fname_base, fname_base, fname_base);
      sprintf(gp_cmd2, "%s plot \"%s.dtf\" u 1:($5>0.1?($9-$4):1/0) title \"fit\" w p pt 7 ps 2 lt 2, \"%s.dtf\" u 1:($5>0.1&&$16==0?($8-$4):1/0):10 w e lt 1 title \"data\",\"%s.dtf\" u 1:($5>0.1&&$16>0?($8-$4):1/0):10 w e lt 3 title \"excluded\"\n", title_cmd, fname_base, fname_base, fname_base);
      
      sprintf(tmp_cmd, "%s set label at %g,%g point ps 10; f(x) = tan(%g)*(x-%g)+%g; plot \"%s.dtf\" u 2:($5<0.1?$3:1/0) title \"zero detectors\" w p lt 3, \"%s.dtf\" u 2:($5>0.1?$3:1/0) title \"event detectors\" w p lt 1",
	      title_cmd, xcore+rusdgeom_.xcore[anal], ycore+rusdgeom_.ycore[anal], init[3]+M_PI, xcore+rusdgeom_.xcore[anal], ycore+rusdgeom_.ycore[anal], fname_base, fname_base);
      strcat(gp_cmd3, tmp_cmd);
      sprintf(tmp_cmd, ", (f(x)>%g&&f(x)<%g)?f(x):1/0 title \"\"\n",
	      yymin, yymax);
      strcat(gp_cmd3, tmp_cmd);
      sprintf(gp_cmd4, "unset logscale xy; %s plot [][] \"%s.dtfx\" u ($2==1?$3-$6:1/0):($4+$5) w l lw 1.5 lt 1 title \"upper\", \"%s.dtfx\" u ($2==0?$3-$6:1/0):($4+$5) w l lw 1 lt 2 title \"lower\"\n",
	    title_cmd, fname_base, fname_base);
      sprintf(gp_cmd5, "unset logscale y; %s set ylabel 'Area/Peak, ns'; a=1000;b=1;f(x)=a*exp(-x*x/2/b);f(x)=a+b*x; fit f(x) \"%s.dtf\" u (($11==0&&$16==0&&$1>=0.5&&$5>0.1)?$1:1/0):($5/$20*20):(1+0*0.5*$5/$20*20*$7/$5) via a,b; plot  \"%s.dtf\" u (($11==0&&$16==0&&$5>0.1)?$1:1/0):($5/$20*20):(0.5*$5/$20*20*$7/$5) w e title \"data\" lt 1, \"%s.dtf\" u ((($11>0||$16>0||$1<0.5)&&$5>0.1)?$1:1/0):($5/$20*20):(0.5*$5/$20*20*$7/$5) w e title \"excluded\" lt 3, f(x), %g + %g*x\n", title_cmd, fname_base, fname_base, fname_base, AOPc0, AOPc1);
      sprintf(fname, "%s/%s.gnu1", OUTDIR, fname_base);
      fil = fopen(fname, "wb"); fprintf(fil, gp_cmd1); fclose(fil); 
      sprintf(fname, "%s/%s.gnu2", OUTDIR, fname_base);
      fil = fopen(fname, "wb"); fprintf(fil, gp_cmd2); fclose(fil); 
      sprintf(fname, "%s/%s.gnu3", OUTDIR, fname_base);
      fil = fopen(fname, "wb"); fprintf(fil, gp_cmd3); fclose(fil); 
      sprintf(fname, "%s/%s.gnu4", OUTDIR, fname_base);
      fil = fopen(fname, "wb"); fprintf(fil, gp_cmd4); fclose(fil); 
      sprintf(fname, "%s/%s.gnu5", OUTDIR, fname_base);
      fil = fopen(fname, "wb"); fprintf(fil, gp_cmd5); fclose(fil); 

      if(cmd_opt.isset("plot")) {
	gp1 = popen("cd " OUTDIR "; gnuplot", "w");
	gp2 = popen("cd " OUTDIR "; gnuplot", "w");
	gp3 = popen("cd " OUTDIR "; gnuplot", "w");
	gp4 = popen("cd " OUTDIR "; gnuplot", "w");
	gp5 = popen("cd " OUTDIR "; gnuplot 2>/dev/null", "w");
	fprintf(gp1, "set mouse;\n"); fprintf(gp2, "set mouse;\n");  fprintf(gp3, "set mouse;\n"); fprintf(gp4, "set mouse;\n"); fprintf(gp5, "set mouse;\n");
	fprintf(gp1, gp_cmd1); 	      fprintf(gp2, gp_cmd2);         fprintf(gp3, gp_cmd3);  	   fprintf(gp4, gp_cmd4);	 fprintf(gp5, gp_cmd5);
	fflush(gp1); 		      fflush(gp2); 		     fflush(gp3);		   fflush(gp4);			 fflush(gp5);
	getchar();
	fprintf(gp1,"exit\n");		fflush(gp1);		pclose(gp1);
	fprintf(gp2,"exit\n");		fflush(gp2);		pclose(gp2);
	fprintf(gp3,"exit\n");		fflush(gp3);		pclose(gp3);
	fprintf(gp4,"exit\n");		fflush(gp4);		pclose(gp4);
	fprintf(gp5,"exit\n");		fflush(gp5);		pclose(gp5);
      }
    }
}

void read_signals(double *init, int db_date, double db_time){
    signal_reader *SR = new signal_reader;
    double theta,phi,t0,aprime,eta,xcore,ycore;
    theta = init[2]; phi = init[3]; t0 = init[4]; aprime = init[6]; eta = fiteta?init[7]:s_eta(theta);
    xcore = init[0]; ycore = init[1];
    for(int c1=0; c1<dcount; c1++) {
      if(dvalue[c1][3]<0.1) continue;
      double x,y,z,r_plane,r,t,t_d;
      x = dvalue[c1][0]-xcore;  y = dvalue[c1][1]-ycore; z = dvalue[c1][2];
      r_plane = sin(theta)*cos(phi)*x + sin(theta)*sin(phi)*y - cos(theta)*z;
      r = sqrt(x*x+y*y+z*z-r_plane*r_plane);
      t = dvalue[c1][4];
      t_d = aprime*linsley_t(r, s_profile(r, theta, eta, r_plane));

      SR->init(db_date, db_time, dxxyy[c1], dsaturated[c1], dvalue[c1][7], r, r_plane + t0 + t_d, dvalue[c1][4]);

      for(int h=0; h<rufptn_.nhits; h++) {
	if( rufptn_.xxyy[h] != dxxyy[c1] || rufptn_.isgood[h]==0) continue;
	for(int wf = rufptn_.wfindex[h];wf<rufptn_.wfindex[h]+rufptn_.nfold[h]; wf++) {
	  for(int c2=0;c2<rusdraw_nchan_sd;c2++) {
	    double tX,u,l;
	    tX = (double(rusdraw_.clkcnt[wf])/double(rusdraw_.mclkcnt[wf])-(rusdgeom_.tearliest - int(rusdgeom_.tearliest)))*1e9
	      + double(c2)*20;
	    tX*=NSEC;
	    u = 1.22*(double(rusdraw_.fadc[wf][1][c2])- double(rusdraw_.pchped[wf][1])/8.0)/rusdraw_.mip[wf][1];
	    l = 1.22*(double(rusdraw_.fadc[wf][0][c2])- double(rusdraw_.pchped[wf][0])/8.0)/rusdraw_.mip[wf][0];
	    SR->feed(tX, u, l);
	  }
	}
	SR->done();
      }	
    }	
    delete SR;
}

bool load_zero(double rmax) {
  xxyy_0=0, signal_0=0;
  for(int sd=0;sd < dcount; sd++) {
    if( dvalue[sd][3] > signal_0) {
      xxyy_0 = dxxyy[sd];
      signal_0 = dvalue[sd][3];
    }
  }
  /*  if(tasdcalibev_.aliveDetLid[0]) {
    for(int c1=0; c1 < tasdcalibev_.numAlive; c1++) {
      if(!tasdcalibev_.aliveDetLid[c1]) break;
      int zero = 1;
      for(int sd=0;sd < rusdgeom_.nsds; sd++) {
	if( tasdcalibev_.aliveDetLid[c1] == rusdgeom_.xxyy[sd]) {
	  zero = 0;
	}
      }
      for(int cx=0;cx<tasdcalibev_.numWf;cx++) {
	if( tasdcalibev_.aliveDetLid[c1] == tasdcalibev_.sub[cx].lid ){
	  zero = 0;
	}
      }
      double x,y,z;
      x = tasdcalibev_.aliveDetPosX[c1]/1200.0 - RUSDGEOM_ORIGIN_X_CLF - rusdgeom_.xcore[anal];
      y = tasdcalibev_.aliveDetPosY[c1]/1200.0 - RUSDGEOM_ORIGIN_Y_CLF - rusdgeom_.ycore[anal];
      z = tasdcalibev_.aliveDetPosZ[c1]/1200.0;
    
      if(zero && (x*x+y*y+z*z)<rmax*rmax) {
	dvalue[dcount][0] = x;
	dvalue[dcount][1] = y;
	dvalue[dcount][2] = z;
	dvalue[dcount][3] = 0;
	dvalue[dcount][4] = 0;
	dvalue[dcount][7] = 0;
	dsaturated[dcount] = 0;
	dxxyy[dcount] = tasdcalibev_.aliveDetLid[c1];
	dcount++;
      }
    }
    return true;
  }
  else {*/
    if(rusdraw_.site<=2) {
      load_zero_tower(rusdraw_.site, rmax);
    }
    else if(rusdraw_.site==3) {
      load_zero_tower(0, rmax);
      load_zero_tower(1, rmax);

    }
    else if(rusdraw_.site==4) {
      load_zero_tower(0, rmax);
      load_zero_tower(2, rmax);
    }
    else if(rusdraw_.site==5) {
      load_zero_tower(1, rmax);
      load_zero_tower(2, rmax);
    }
    else if(rusdraw_.site==6) {
      load_zero_tower(0, rmax);
      load_zero_tower(1, rmax);
      load_zero_tower(2, rmax);
    }
    else {
      fprintf(stderr, "We don't know intersite configuration for MC tower=%i\n", rusdraw_.site);
      exit(1);
    }
    return true;
}

bool load_zero_tower(int tower, double rmax) {
    int x0, y0;
    x0 = xxyy_0 / 100;
    y0 = xxyy_0 % 100;
    if(tower>2) {
      fprintf(stderr, "BUG A98765\n");
      exit(1);
    }
    for(int c1 = 0; c1 < xxyy_num[tower]; c1++) {
      int newx, newy;
      newx = xxyy[tower][c1]/100;
      newy = xxyy[tower][c1]%100;
      if( (double(newx) - double(x0))*(double(newx) - double(x0))
          + (double(newy) - double(y0))*(double(newy) - double(y0)) < rmax*rmax ) {
        int zero = 1;
        for(int sd=0;sd < rusdgeom_.nsds; sd++) {
          if( newx*100+newy == rusdgeom_.xxyy[sd]) {
            zero = 0;
          }
        }
	if(tasdcalibev_.numDead) {
	  for(int c1=0; c1 < tasdcalibev_.numDead; c1++) {
	    if( newx*100+newy == tasdcalibev_.deadDetLid[c1]) {
	      zero = 0;
	    }
	  }
	}
        if(zero) {
          double x,y;
          x = double(newx)-rusdgeom_.xcore[anal];
          y = double(newy)-rusdgeom_.ycore[anal];
          dvalue[dcount][0] = x;
          dvalue[dcount][1] = y;
          dvalue[dcount][2] = 0;
          dvalue[dcount][3] = 0;
          dvalue[dcount][4] = 0;
	  dvalue[dcount][7] = 0;
          dsaturated[dcount] = 0;
          dcount++;
        }       
      } 
    }
    return true;
}

bool fix_site() {
  int towerflag=0;
  int tower=0;
  // set the labels for the sites which participate in event reconstruction
  for (int jj=0; jj < rusdraw_.nofwf; jj ++ )
    {
      int xxyy0 = rusdraw_.xxyy[jj];
      for(int s1=0;s1<3;s1++) {
	for(int c1=0;c1<xxyy_num[s1];c1++) {
	  if(xxyy0 == xxyy[s1][c1]) {
	    towerflag |= (1<<s1);
	  }
	}
      }
    }
  switch ( (int)(towerflag & 7) )
    {
    case 7:
      {
        tower = RUSDRAW_BRLRSK;
        break;
      }
    case 3:
      {
        tower = RUSDRAW_BRLR;
        break;
      } 
    case 5:
      {
        tower = RUSDRAW_BRSK;
        break;
      }      
    case 6:
      {
        tower = RUSDRAW_LRSK; 
        break;
      }      
    case 1:
      {
        tower  = RUSDRAW_BR;
        break;
      }
    case 2:
      {
        tower = RUSDRAW_LR;
        break;
      }
    case 4:
      {
        tower = RUSDRAW_SK;
        break;
      }
    default:
      {
        tower = 0;
       break;
      }
    }
  if(tower != rusdraw_.site) {
    printf("Tower is fixed from %i ", rusdraw_.site);
    rusdraw_.site = tower;
    printf("to %i, nwf = %i, dataset = %i\n", rusdraw_.site, rusdraw_.nofwf, n_dataset);
    return true;
  }
  return false;
}
