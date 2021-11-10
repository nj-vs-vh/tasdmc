/******************************  CLASS FOR SIGNAL ANALYSIS ********************************************/

#define WAVE_THRESH 0.2
#define COUNT_THRESH 3

class signal_reader {
 public:
  bool init(int event_d, double event_t, int xxyy, bool saturated, bool gex, double r, double t_fit, double t_data);
  bool feed(double t, double u, double l);
  bool done(int error=0);
  bool dump(int error);

 protected:
  void wadd(double u, double l);
  void wcln();

  int event_d;
  double event_t;
  int xxyy;
  bool saturated;
  bool gex;
  double r;
  double t_fit;  // t0 from fit
  double t_data; // t0 datapoint

  double t_start; // signal start time
  int idx; // bin index

  int wave_num; // number of waves
  bool in_wave; // 1 - inside wave, 0 - outside
  int switch_count; // COUNT_THRESH bins above WAVE_THRESH and we switch in_wave

  int idx_start, idx_end;
  double u_sum, l_sum, u_max, l_max;
  int u_peaks, l_peaks;

};

/*******************************************************************************************************/
