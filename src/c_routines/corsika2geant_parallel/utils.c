#include "./utils.h"

void standardNormalPairBM(double pair[2]) // Box-Muller method
{
    double r, phi;
    r = sqrt(-2.0 * log(drand48()));
    phi = 2 * PI * drand48();
    pair[0] = (r * cos(phi));
    pair[1] = (r * sin(phi));
}
