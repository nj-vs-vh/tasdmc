#define CSPEED 29.97925
#define PI 3.14159265359
#define MAXHEIGHT 100000.e2 /* 10km */
#define RADDEG 57.29577951
#define BLURFACTOR 5.0
#define GEV_PER_GM 0.01
#define ECCEN 0.0
#define SM pow(1.-ECCEN*ECCEN, -0.25)
#define TRUNC 1.0
#define ENRES 0.1
#define ATMOS_MODEL 25

void weightPrep_t(float buf[], float R0[], float d1[], float R1[], 
		  float *energy, float *dist, float *R, float pln1[], 
		  float pln2[], float *latdist, float *mo);
void weightThrow(float d1[], float R1[], float pln1[], float pln2[],
		 float R, float energy, float dist, 
		 float t, float spread, float output[],
		 int parttype, float mo);
void polar_gaussf(float pair[], float trunc);
void crossf(float v1[], float v2[], float v3[]);
float dotf( float u[], float v[]);
float normalizef( float v[], float vhat[]);
void gaussf(float pair[]);

#define  DISTMED 500.
#define  DISTA 400.
#define  DISTB 520.
#define  DISTMAX 8415.
#define  NSUBBLOCK 21
#define  NSENTENCE 39
#define  NPART 8
#define  NWORD NPART*NSENTENCE
#define  NPART2 7
#define  NWORD2 NPART2*NSENTENCE
#define  RM 88.e2
#define  RN 1100.e2
static const float pmass[26]={0.,0.,0.511e-3,.511e-3,0.,105.7e-3,105.7e-3,135.e-3,
			      140.e-3,140.e-3,498.e-3,494.e-3,494.e-3,940.e-3,938.e-3,
			      938.e-3,498.e-3,549.e-3,1116.e-3,1189.e-3,1193.e-3,
			      1197.e-3,1315.e-3,1321.e-3,1672e-3,940.e-3};
float coszenith;
float origin[3], normorig[3];
float Z0;
