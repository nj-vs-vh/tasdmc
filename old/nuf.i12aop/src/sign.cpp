#include "nuf.h"


bool signal_reader::init(int event_d, double event_t, int xxyy, bool saturated, bool gex, double r, double t_fit, double t_data) {
  this->event_d = event_d; this->event_t = event_t; this->xxyy = xxyy;
  this->saturated = saturated; this->gex = gex;
  this->r = r; this->t_fit = t_fit; this->t_data = t_data;

  this->t_start = 0; this->idx = 0; this->wave_num = 0;
  wcln();
  return true;
}

bool signal_reader::feed(double t, double u, double l) {
  if(idx==0) { // first feed
    t_start = t;
  }
  else if( fabs(t-t_start-idx*20*NSEC) > 10*NSEC) {
    if(in_wave && fabs(t-t_start-idx*20*NSEC) < 80*NSEC) {
      done(myround((t-t_start)/NSEC-idx*20));
    }
    else {
      done();
    }
    t_start = t;
  }
  idx++;

  if(!in_wave) {
    if( u + l < WAVE_THRESH) {
      wcln();
      return true;
    }
    else {
      switch_count++;
      if(switch_count>=COUNT_THRESH) {
	in_wave = true;
      }
      if(switch_count==1) {
	idx_start = idx - 1;
      }
      wadd(u,l);
      return true;
    }
  }
  else {
    if( u + l < WAVE_THRESH) {
      switch_count++;
      if(switch_count>=COUNT_THRESH) {
	in_wave = false;
	idx_end = idx-COUNT_THRESH;
	wave_num++;
	dump(0);
	wcln();
	return true;
      }
    }
    wadd(u,l);
    return true;
  }
  return false;
}

void signal_reader::wadd(double u, double l) {
  u_sum += u; l_sum += l; u_max = fmax(u, u_max); l_max = fmax(l, l_max);
}

void signal_reader::wcln() {
  switch_count = 0; u_sum = 0; l_sum = 0; u_max = 0; l_max = 0; u_peaks = 0; l_peaks = 0; idx_start = 0; idx_end = 0;
}

bool signal_reader::done(int error) {
  if(in_wave) {
    in_wave = false;
    idx_end = idx-1;
    wave_num++;
    dump(error>0?error:1);
  }
  wcln();
  idx = 0;
  in_wave = false;
  return true;
}

bool signal_reader::dump(int error) {
  printf("DBSIG %i %.6f %s%i %i %i %.2f %.4f %5i %5i"
	 " %i %3i %2i %6.2f %6.2f %5.2f %5.2f %i %i %i %s\n",
	 event_d, event_t, (xxyy>=1000)?"":"0", xxyy, saturated, gex, r,
	 t_data, myround((t_fit-t_data)/NSEC), myround((t_start - t_data)/NSEC + idx_start*20),
	 wave_num, idx_start, idx_end-idx_start+1, u_sum, l_sum, u_max, l_max, u_peaks, l_peaks, error, (error==1?"WFCUT":(error>1?"WFGAP":"")));
  return true;
}

int myround(double f) {
  return int(floor(f+0.5));
}
