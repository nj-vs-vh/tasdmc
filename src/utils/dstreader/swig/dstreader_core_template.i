%module dstreader_core
%{
#include "event.h"
#define SWIG_FILE_WITH_INIT
%}

// numpy interface boilerplate
%include "numpy.i"
%init %{
import_array();
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

// making functions return string on Python side instead of modifying char * arg inplace
%include "cstring.i"
// other functions with char * argument may be mapped the same way
// on Python side signature is integer4_return_value, name = eventNameFromId(bank, len)
%cstring_bounded_output(integer1 *name, 1024);
integer4 eventNameFromId(integer4 bank, integer1 *name, integer4 len);
%ignore eventNameFromId;  // ignoring unmapped version from event.h

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
// if the banks also include arrays in them, custom numpy accessors should be generated for
// them with generate_numpy_accessors.py; see setup.py InstallWithSwig class for details
%include "rusdmc_dst.h"
%include "rusdraw_dst.h"

// generated numpy accessors will be appended here
