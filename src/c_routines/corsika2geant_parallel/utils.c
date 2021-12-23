#include <math.h>
#include <stdlib.h>

#include "./utils.h"

void getStandardNormalPair(double *pair) // Box-Muller method
{
    double r, phi;
    r = sqrt(-2.0 * log(drand48()));
    phi = 2 * PI * drand48();
    pair[0] = (r * cos(phi));
    pair[1] = (r * sin(phi));
}
