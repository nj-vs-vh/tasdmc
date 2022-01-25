%module dstreader_core
%{
#include "event.h"
%}

// marking or variables as immutable = read-only
%immutable;

// for creating, dereferencing and freeing int pointers from Python
// see http://www.swig.org/Doc3.0/Library.html#Library_nn4
%include "cpointer.i"
%pointer_functions(int, intp);
%pointer_functions(char, strp);

// %include "typemaps.i"
%include "cstring.i"

// using SWIG's typemaps.i to make eventNameFromId return second string arg
%cstring_bounded_output(integer1 *name, 1024);
integer4 eventNameFromId(integer4 bank, integer1 *name, integer4 len);

// basic dst file manipulation functions
%ignore eventNameFromId;
%include "event.h"
// definition for fortran-esque like integer4 and real8
%include "dst_std_types.h"
// constants' definitions
%include "univ_dst.h"
%include "dst_size_limits.h"
// bank list manipulations
%include "bank_list.h"



// actual banks to be exposed to Python, may be appended with %include "<bankname>_dst.h"
%include "rusdraw_dst.h"
%include "rusdmc_dst.h"
