#include <gsl/gsl_math.h>
#include <gsl/gsl_multimin.h>

typedef double (*t_prob_fun)(const gsl_vector *, void *);

double do_fit(int params_num, double *init, double isteps[], t_prob_fun f, int MAX_ITER);

