void weightPrep_t(float buf[], float R0[], float d1[], float R1[],
				  float *energy, float *dist, float *R, float pln1[],
				  float pln2[], float *latdist, float *mo);
void weightThrow(float d1[], float R1[], float pln1[], float pln2[],
				 float R, float energy, float dist,
				 float t, float spread, float output[],
				 int parttype, float mo);
void polar_gaussf(float pair[], float trunc);
void crossf(float v1[], float v2[], float v3[]);
float dotf(float u[], float v[]);
float normalizef(float v[], float vhat[]);
void gaussf(float pair[]);
