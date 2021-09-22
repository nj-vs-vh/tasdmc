/* 
   This variable tells how much memory to use per corsika2geant process
   (NT variable roughly equals (memory in Gb) x 16)
   One should pass -DNT=32 (or some other number) on the command line 
   when compiling the program.
 */
#ifndef NT
#error Array size variable 'NT' has not been defined. Use -DNT=16,64, etcon the command line to compile the code
#endif

double corsika_times_th(char *filename);
double corsika_vem_th(char *filename, int tcount);
double corsika_times(char *filename);
double corsika_vem(char *filename, char *tmpfile, int tcount);
double corsika_vem_init(char *filename, char *tmpfile, int tcount);
void fill_time();
void fill_vem();
#define  NSENTENCE 39
#define  NPART 7
#define  NWORD NPART*NSENTENCE
#define NSUBBLOCK 21
#define PARTSIZE 7
static const float pmass[26]={0.,0.,0.511e-3,.511e-3,0.,105.7e-3,105.7e-3,135.e-3,
			      140.e-3,140.e-3,498.e-3,494.e-3,494.e-3,940.e-3,938.e-3,
			      938.e-3,498.e-3,549.e-3,1116.e-3,1189.e-3,1193.e-3,
			      1197.e-3,1315.e-3,1321.e-3,1672e-3,940.e-3};


float eventbuf[NWORD];
float origin[3], zenith;

#define DISTMAX 8400 /* Meters / 10.0 */
#define NX DISTMAX/3
#define NY DISTMAX/3
#define DT 20
#define FRAC 0.99
#define EMIN 0.003
#define VEM 2.05 /* MeV */
#define SRL 0.06
#define CSPEED 29.97925 /* cm/nsec */
#define TMAX 1280
#define PI 3.14159265359

float time1[NX][NY], tmin, filldist, emin;
int dm, dn;
unsigned short vemcount[NX][NY][NT][2];
unsigned short pz[NX][NY][NT];
