#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/types.h>
#include <assert.h>
#include <libgen.h>
#include <errno.h>

#include "constants.h"
#include "atmosphere.h"
#include "globals.h"
#include "corsika_weights.h"


void weightPrep_t(float buf[], float R0[], float d1[], float R1[],
				  float *energy, float *dist, float *R, float pln1[],
				  float pln2[], float *latdist,
				  float *mo)
{
	int i, parttype /* Corsika particle type number */;
	float EO[3], pEO, tc, mEO, sectheta, Rtmp;
	float hadgen /* hadron generation number */;
	parttype = (int)(buf[0] / 1000.);
	hadgen = floorf((buf[0] - (float)parttype * 1000.) / 10.);
	if (hadgen > 50.)
		hadgen -= 50.;
	R1[0] = buf[1];
	R1[1] = buf[2];
	R1[2] = -buf[3];
	*energy = hypotf(buf[1], hypotf(buf[2], buf[3]));
	sectheta = (*energy) / buf[3];
	*energy = hypotf(pmass[parttype], (*energy));
	normalizef(R1, R1);
	pln1[0] = -R1[1];
	pln1[1] = R1[0];
	pln1[2] = 0.;
	normalizef(pln1, pln1);
	crossf(R1, pln1, pln2);
	normalizef(pln2, pln2);
	d1[0] = buf[4];
	d1[1] = buf[5];
	d1[2] = Z0;
	*latdist = hypotf(d1[0] * coszenith, d1[1]);
	d1[2] = 0.;
	*dist = normalizef(d1, d1);
	EO[0] = buf[4];
	EO[1] = buf[5];
	EO[2] = Z0;
	for (i = 0; i < 3; i++)
		EO[i] = origin[i] - EO[i];
	pEO = dotf(R1, EO);
	mEO = normalizef(EO, EO);
	tc = buf[6] * CSPEED;
	*R = (tc * tc - mEO * mEO) / (tc + pEO) / 2.0;
	Rtmp = (((float)h2mo(Z0, ATMOS_MODEL) -
			 (float)h2mo(origin[2], ATMOS_MODEL)) /
			EO[2]) -
		   (30. * hadgen);
	Rtmp = ((float)mo2h(((float)h2mo(Z0, ATMOS_MODEL) -
						 Rtmp * EO[2]),
						ATMOS_MODEL) -
			Z0) /
		   EO[2];
	if (Rtmp > 0 && *R > Rtmp)
		*R = Rtmp;
	*mo = ((float)h2mo(Z0, ATMOS_MODEL) -
		   (float)h2mo((-R1[2] * (*R) + Z0), ATMOS_MODEL)) *
		  sectheta;
	return;
}

void weightThrow(float d1[], float R1[], float pln1[], float pln2[],
				 float R, float energy, float dist,
				 float t, float spread, float output[],
				 int parttype, float mo)

{
	int k;
	float R2[3], gp[2], pert1, pert2;
	float sectheta, mo2, ptot, dt, prob_decay, dmo;
	polar_gaussf(gp, TRUNC);
	pert1 = sqrtf(1 / cosf(gp[0] * spread / SM) / cosf(gp[0] * spread / SM) - 1.);
	pert2 = sqrtf(1 / cosf(gp[0] * spread * SM) / cosf(gp[0] * spread * SM) - 1.);
	for (k = 0; k < 3; k++)
	{
		R2[k] = R1[k] + pert1 * cosf(gp[1]) * pln1[k] +
				pert2 * sinf(gp[1]) * pln2[k];
	}
	normalizef(R2, R2);
	sectheta = hypotf(R2[0], hypotf(R2[1], R2[2])) / -R2[2];
	mo2 = ((float)h2mo(Z0, ATMOS_MODEL) - (float)h2mo((-R1[2] * R + Z0),
													  ATMOS_MODEL)) *
		  sectheta;
	dmo = mo2 - mo;
	prob_decay = expf(-dmo / 50. * coszenith * coszenith);
	dt = (R1[2] / R2[2] - 1.) * R / CSPEED;
	if (R2[2] >= 0. || drand48() > (double)prob_decay)
	{
		output[1] = 1.;
		output[2] = 1.;
		output[3] = -100.;
		output[4] = DISTMAX * 200.;
		output[5] = DISTMAX * 200.;
		output[6] = 1.e7;
	}
	else
	{
		gaussf(gp);
		energy *= 1. + ENRES * gp[0];
		ptot = sqrt(energy * energy - pmass[parttype] * pmass[parttype]);
		output[1] = ptot * R2[0];
		output[2] = ptot * R2[1];
		output[3] = -ptot * R2[2];
		output[4] = dist * d1[0] + R * (R2[0] * R1[2] / R2[2] - R1[0]);
		output[5] = dist * d1[1] + R * (R2[1] * R1[2] / R2[2] - R1[1]);
		output[6] = t + dt;
	}

	return;
}

void polar_gaussf(float pair[], float trunc)
{
	double r, phi, randnum = 1;
	randnum = 1. - (double)trunc * drand48();
	r = sqrt(-2.0 * log(randnum));
	phi = 2 * PI * drand48();
	pair[0] = (float)r;
	pair[1] = (float)phi;
	return;
}

void gaussf(float pair[])
{
	double r, phi;
	r = sqrt(-2.0 * log(drand48()));
	phi = 2 * PI * drand48();
	pair[0] = (float)(r * cos(phi));
	pair[1] = (float)(r * sin(phi));
	return;
}

void crossf(float v1[], float v2[], float v3[])
{

	v3[0] = v1[1] * v2[2] - v1[2] * v2[1];
	v3[1] = v1[2] * v2[0] - v1[0] * v2[2];
	v3[2] = v1[0] * v2[1] - v1[1] * v2[0];
	return;
}

float dotf(float u[], float v[])
{
	float s;
	s = u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
	return s;
}

float normalizef(float v[], float vhat[])
{

	float norm;

	norm = sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);

	if (norm <= 0.0)
	{
		vhat[0] = 0.0;
		vhat[1] = 0.0;
		vhat[2] = 0.0;
		norm = 0.0;
		return norm;
	}

	vhat[0] = v[0] / norm;
	vhat[1] = v[1] / norm;
	vhat[2] = v[2] / norm;
	return norm;
}
