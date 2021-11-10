#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>


#define NSDEDGELINES 11

// T-shape borders
#define NSDTSHAPELINESBR 2
#define NSDTSHAPELINESLR 2
#define NSDTSHAPELINESSK 1 



///////DESCRIPTION OF LINES WHICH DEFINE THE BOUNDAY.  THE BOUNDARIES SHOULD BE CONVEX. ////////////////

// Definitions of border lines for the edgre of the arrray
static double sdedgelinesRAW[NSDEDGELINES][4] = 
  {
    {6.,1.,18.,1.},
    {18.,1.,24.,8.},
    {24.,8.,24.,12.},
    {24.,12.,23.,17.},
    {23.,17.,21.,23.},
    {21.,23.,19.,28.},
    {19.,28.,15.,28.},
    {15.,28.,11.,26.},
    {11.,26.,1.,16.},
    {1.,16.,1.,6.},
    {1.,6.,6.,1.}
  };
static double sdtshapelinesRAWBR[NSDTSHAPELINESBR][4] = 
  {
    {22.,19.,13.,19.},
    {13.,19.,13.,1.,}    
  };
static double sdtshapelinesRAWLR[NSDTSHAPELINESLR][4] = 
  {
    {12.,1.,12.,19.},
    {12.,19.,4.,19.}
  };
static double sdtshapelinesRAWSK[NSDTSHAPELINESSK][4] = 
  {
    {5.,20.,22.,20.}
  };


// array of central x,y values for each border line and
// unit vectors perpendicular to each borer lines
// and pointing INSIDE the array
static double sdedgelines    [NSDEDGELINES][4];
static double sdtshapelinesBR[NSDTSHAPELINESBR][4];
static double sdtshapelinesLR[NSDTSHAPELINESLR][4];
static double sdtshapelinesSK[NSDTSHAPELINESSK][4];




static void prepSDborders()
{
  int iborder;
  double dX,dY;

  double xc,yc;
  double vx,vy;
  

  // prepare SD array edge boundaries
  for (iborder=0; iborder < NSDEDGELINES; iborder++)
    {
      dX = sdedgelinesRAW[iborder][2] - sdedgelinesRAW[iborder][0];
      dY = sdedgelinesRAW[iborder][3] - sdedgelinesRAW[iborder][1];
      
      // Central X and Y values for each border line
      xc = sdedgelinesRAW[iborder][0] + dX / 2.0;
      yc = sdedgelinesRAW[iborder][1] + dY / 2.0;
      
      // unit vector perpendicular to the border line
      vx = -dY / sqrt ( dX * dX + dY * dY); 
      vy =  dX / sqrt ( dX * dX + dY * dY);
      
      // Make sure that the unit vector points INSIDE the array,
      // i.e. point (12,14) should have positive dot product wit the unit vector
      if ( (vx * (12.0-xc) + vy*(14.0-yc)) < 0.)
	{
	  vx *= -1.;
	  vy *= -1.;
	}
      sdedgelines[iborder][0] = xc;
      sdedgelines[iborder][1] = yc;
      sdedgelines[iborder][2] = vx;
      sdedgelines[iborder][3] = vy;      
    }


  // prepare BR T-Shape boundaries
  for (iborder=0; iborder < NSDTSHAPELINESBR; iborder++)
    {
      dX = sdtshapelinesRAWBR[iborder][2] - sdtshapelinesRAWBR[iborder][0];
      dY = sdtshapelinesRAWBR[iborder][3] - sdtshapelinesRAWBR[iborder][1];
      
      // Central X and Y values for each border line
      xc = sdtshapelinesRAWBR[iborder][0] + dX / 2.0;
      yc = sdtshapelinesRAWBR[iborder][1] + dY / 2.0;
      
      // unit vector perpendicular to the border line
      vx = -dY / sqrt ( dX * dX + dY * dY); 
      vy =  dX / sqrt ( dX * dX + dY * dY);
      
      
      if ( (vx * (17.0-xc) + vy*(11.0-yc)) < 0.)
	{
	  vx *= -1.;
	  vy *= -1.;
	}
      sdtshapelinesBR[iborder][0] = xc;
      sdtshapelinesBR[iborder][1] = yc;
      sdtshapelinesBR[iborder][2] = vx;
      sdtshapelinesBR[iborder][3] = vy;      
    }


  

    // prepare LR T-Shape boundaries
  for (iborder=0; iborder < NSDTSHAPELINESLR; iborder++)
    {
      dX = sdtshapelinesRAWLR[iborder][2] - sdtshapelinesRAWLR[iborder][0];
      dY = sdtshapelinesRAWLR[iborder][3] - sdtshapelinesRAWLR[iborder][1];
      
      // Central X and Y values for each border line
      xc = sdtshapelinesRAWLR[iborder][0] + dX / 2.0;
      yc = sdtshapelinesRAWLR[iborder][1] + dY / 2.0;
      
      // unit vector perpendicular to the border line
      vx = -dY / sqrt ( dX * dX + dY * dY); 
      vy =  dX / sqrt ( dX * dX + dY * dY);
      
      
      if ( (vx * (7.0-xc) + vy*(11.0-yc)) < 0.)
	{
	  vx *= -1.;
	  vy *= -1.;
	}
      sdtshapelinesLR[iborder][0] = xc;
      sdtshapelinesLR[iborder][1] = yc;
      sdtshapelinesLR[iborder][2] = vx;
      sdtshapelinesLR[iborder][3] = vy;      
    }




  // prepare SK T-Shape boundaries
  for (iborder=0; iborder < NSDTSHAPELINESSK; iborder++)
    {
      dX = sdtshapelinesRAWSK[iborder][2] - sdtshapelinesRAWSK[iborder][0];
      dY = sdtshapelinesRAWSK[iborder][3] - sdtshapelinesRAWSK[iborder][1];
      
      // Central X and Y values for each border line
      xc = sdtshapelinesRAWSK[iborder][0] + dX / 2.0;
      yc = sdtshapelinesRAWSK[iborder][1] + dY / 2.0;
      
      // unit vector perpendicular to the border line
      vx = -dY / sqrt ( dX * dX + dY * dY); 
      vy =  dX / sqrt ( dX * dX + dY * dY);
      
      if ( (vx * (15.0-xc) + vy*(23.0-yc)) < 0.)
	{
	  vx *= -1.;
	  vy *= -1.;
	}
      sdtshapelinesSK[iborder][0] = xc;
      sdtshapelinesSK[iborder][1] = yc;
      sdtshapelinesSK[iborder][2] = vx;
      sdtshapelinesSK[iborder][3] = vy;      
    }


  

}



/* 
   INPUTS: x,y in [1200m] units with respect to SD origin

   OUTPUTS:

   b[2] - unit vector, points inside SD array, perpendicular to 
   closest boundary line
   bdist - distance along that vector.  It is positive if the point
   is inside the array and negative if the point is outside of the array




   FOR T-SHAPE BOUNDARY:
   tbr[2] - unit vect, perpendicular to closest BR T-Shape boundary,
   pointing inside the BR subarray
   
   tdistbr - distance along that vector.  Is negative if the point
   is outside of the BR subarray
   

   Simular for LR, SK subarrays
   tlr[2]
   tdistlr
   tsk[2]
   tdistks

   For all points inside the SD array (bdist is positive), AT MOST ONE
   from tdistbr,tdistlr,tdistsk  is positive, which corresponds
   to the case that the point is in one of the subarrays.  If a point
   is in neither subarrays, then all 3 distances will be negative.
   
 */

void sdbdist(double x, double y, 
	     double *b,  double *bdist, 
	     double *tbr,double *tdistbr, 
	     double *tlr,double *tdistlr,
	     double *tsk,double *tdistsk)
{
  static int prepborders = 0;  
  double dist,mindist;
  int iborder,imin;
  double xc,yc;
  double vx,vy;
  if (prepborders ==0)
    {
      prepSDborders();
      prepborders = 1;
    }
  
  // for SD edege boundaries
  imin = 0;
  mindist=1.e8;
  for ( iborder=0; iborder<NSDEDGELINES; iborder++)
    {
      xc = sdedgelines[iborder][0];
      yc = sdedgelines[iborder][1];
      vx = sdedgelines[iborder][2];
      vy = sdedgelines[iborder][3];
      dist = (x-xc)*vx + (y-yc)*vy; 
      if ( dist < mindist)
	{  
	  imin = iborder;
	  mindist = dist; 
	}
    }
  (*bdist)    =  mindist;
  memcpy (&b[0],&sdedgelines[imin][2],2*sizeof(double));


  

  // For BR T-Shape
  imin = 0;
  mindist=1.e8;
  for ( iborder=0; iborder<NSDTSHAPELINESBR; iborder++)
    {
      xc = sdtshapelinesBR[iborder][0];
      yc = sdtshapelinesBR[iborder][1];
      vx = sdtshapelinesBR[iborder][2];
      vy = sdtshapelinesBR[iborder][3];
      dist = (x-xc)*vx + (y-yc)*vy; 
      if ( dist < mindist)
	{  
	  imin = iborder;
	  mindist = dist; 
	}
    }
  (*tdistbr)    =  mindist;
  memcpy (&tbr[0],&sdtshapelinesBR[imin][2],2*sizeof(double));

  

  // For LR T-Shape
  imin = 0;
  mindist=1.e8;
  for ( iborder=0; iborder<NSDTSHAPELINESLR; iborder++)
    {
      xc = sdtshapelinesLR[iborder][0];
      yc = sdtshapelinesLR[iborder][1];
      vx = sdtshapelinesLR[iborder][2];
      vy = sdtshapelinesLR[iborder][3];
      dist = (x-xc)*vx + (y-yc)*vy; 
      if ( dist < mindist)
	{  
	  imin = iborder;
	  mindist = dist; 
	}
    }
  (*tdistlr)    =  mindist;
  memcpy (&tlr[0],&sdtshapelinesLR[imin][2],2*sizeof(double));

  // For SK T-Shape
  imin = 0;
  mindist=1.e8;
  for ( iborder=0; iborder<NSDTSHAPELINESSK; iborder++)
    {
      xc = sdtshapelinesSK[iborder][0];
      yc = sdtshapelinesSK[iborder][1];
      vx = sdtshapelinesSK[iborder][2];
      vy = sdtshapelinesSK[iborder][3];
      dist = (x-xc)*vx + (y-yc)*vy; 
      if ( dist < mindist)
	{  
	  imin = iborder;
	  mindist = dist; 
	}
    }
  (*tdistsk)    =  mindist;
  memcpy (&tsk[0],&sdtshapelinesSK[imin][2],2*sizeof(double));
  
}
