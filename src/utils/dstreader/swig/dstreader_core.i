%module dstreader_core
%{
#include "event.h"
%}

// marking all variables as immutable = read-only
// this is not only because we're building a 'reader',
// but also because array element assignments lead
// to errors in generated interface code for some reason...
%immutable;

// for creating, dereferencing and freeing pointers from Python
// see http://www.swig.org/Doc3.0/Library.html#Library_nn4
%include "cpointer.i"
%pointer_functions(int, intp);

// %include "typemaps.i"
%include "cstring.i"

// making eventNameFromId return name string on Python side instead
// of modifying passed arg
%cstring_bounded_output(integer1 *name, 1024);
integer4 eventNameFromId(integer4 bank, integer1 *name, integer4 len);
%ignore eventNameFromId;  // to ignore its later version from included event.h

// basic dst file manipulation functions
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
