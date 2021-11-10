#include <stdio.h>
#include "fit.hpp"
#include "nuf.h"


double do_fit(int params_num, double *init, double isteps[], t_prob_fun f, int MAX_ITER){
  gsl_set_error_handler_off();
  double rvalue;
  const gsl_multimin_fminimizer_type *mType = gsl_multimin_fminimizer_nmsimplex2;
  gsl_multimin_fminimizer *Minimizer = NULL;

  gsl_multimin_function mm_func;
  mm_func.f = f;
  mm_func.n = params_num;
  mm_func.params = NULL;

  gsl_vector *initial, *steps;
  initial = gsl_vector_alloc(params_num);
  steps = gsl_vector_alloc(params_num);

  for(int c1=0;c1<params_num;c1++) {
    gsl_vector_set(initial,c1,init[c1]);
    gsl_vector_set(steps,c1,isteps[c1]);
  }

  Minimizer = gsl_multimin_fminimizer_alloc(mType,params_num);
  gsl_multimin_fminimizer_set(Minimizer,&mm_func,initial,steps);

  int iteration = 0;
  int status = 0;
  double size;

  do {
    ++iteration;
    if(cmd_opt.isset("fitdebug")) {
      printf("Iteration: %5d ", iteration);
      for(int c1 = 0; c1<params_num; ++c1) {
	printf("%9.3g ", gsl_vector_get(Minimizer->x, c1));
      }
      printf("f() = %2.5g size = %.3g\n", Minimizer->fval, size);
      for(int c1=0;c1<params_num;c1++) {
	init[c1] = gsl_vector_get(Minimizer->x,c1);
      }
      plot_dtf(init, Minimizer->fval);
    }

    status = gsl_multimin_fminimizer_iterate(Minimizer);
    if (status) break;

    size = gsl_multimin_fminimizer_size (Minimizer);
    status = gsl_multimin_test_size (size, 2e-4);

#ifdef do_debug
    if(status == GSL_SUCCESS) {
      printf("Minimum: ");
      printf("%5d ", iteration);
      for(int c1 = 0; c1<params_num; ++c1) {
	printf("%9.3g ", exp(gsl_vector_get(Minimizer->x, c1)));
      }
      printf("f() = %2.5g size = %.3g\n", Minimizer->fval, size);
    }
    
#endif
  }
  while (status == GSL_CONTINUE && iteration < MAX_ITER);

  for(int c1=0;c1<params_num;c1++) {
    init[c1] = gsl_vector_get(Minimizer->x,c1);
  }

  fit_final_size = size;

  if(iteration==MAX_ITER) {
    size = gsl_multimin_fminimizer_size (Minimizer);
    status = gsl_multimin_test_size (size, 1e-2);
    if(status == GSL_SUCCESS) {
    }
    else {
      if(cmd_opt.isset("v") && MAX_ITER>-500) {
	fprintf(stderr, "Fit failed after %i iterations\n", MAX_ITER);
      }
    }
  }
  rvalue = Minimizer->fval;
  gsl_multimin_fminimizer_free(Minimizer);
  gsl_vector_free(initial);
  gsl_vector_free(steps);
  return rvalue;
}

