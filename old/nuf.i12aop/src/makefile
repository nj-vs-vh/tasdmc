SHELL           = /bin/sh


# ************* WHERE TO FIND LIBRARIES AND INCLUDES ***************************

# DST LIBRARIES AND INCLUDE FILES
DSTDIR= $(shell pwd)/../../dst2k-ta


# SD ANALYSIS LIBRARIES AND INCLUDES
SDLIBDIR = $(shell pwd)/../../lib
SDINCDIR = $(shell pwd)/../../inc

# SD MONITORING INCLUDES
INCDIR  =  $(shell pwd)/../inc

# BINARY FILES
BINDIR  =  $(shell pwd)/../bin


# ******* PUTTING TOGETHER ALL LIBRARIES AND INCLUDES ***************************

INCS =  -I$(DSTDIR)/inc -I$(SDINCDIR) -I$(INCDIR)

# General libraries
LIBS =  -L/lib -lm -lz -lbz2 -lgsl -lgslcblas

# add dst libraries
LIBS += -L$(DSTDIR)/lib -ldst2k

# add SD libs
LIBS += -L$(SDLIBDIR) -lsduti $(rufptnlflag)


# ******* SETTING UP COMPILERS, THEIR FLAGS, LINKER, AND LINKED LIBRARIES ************

CPP           = g++
CPPFLAGS      = -g -Wall -fPIC $(INCS)
LD            = g++
LDFLAGS       = 
LDLIBS        = $(LIBS)


# ******************** SETTING THE SUFFIXES *******************************************

ObjSuf        = o
cppSrcSuf     = cpp
OutPutOpt     = -o # keep whitespace after "-o"




# ************ ASSIGNING NAMES TO SOURCES, OBJECTS, AND PROGRAMS *********************

SDITERATOR= nuf

# Add any cpp sources here
CPPSRCS	= nuf.cpp cmdoptions.cpp sdrunclass.cpp iterate.cpp fit.cpp sdparamborder.cpp sign.cpp

# Make a list of object files based on the sources
OBJS	+= ${CPPSRCS:.$(cppSrcSuf)=.$(ObjSuf)}
OBJS    += $(FORSRCS:.$(forSrcSuf)=.$(ObjSuf))

PROGRAMS = $(SDITERATOR)


# ************** INSTRUCTIONS HOW TO PUT TOGETHER THE PROGRAM ************************

all:	$(PROGRAMS)


# how to build the nuf program
$(SDITERATOR):$(OBJS)
		$(LD) $(LDFLAGS) $^ $(LDLIBS) $(OutPutOpt)$@
		@mv $@ $(BINDIR)/.
		@echo "$@ done"

clean: 
		@rm -f $(OBJS) core $(BINDIR)/$(SDITERATOR)
		@rm *~ -f

distclean:	clean
		$(MAKE)


# ************** SUFFIX RULES (HOW TO TURN SOURCES INTO OBJECTS) *********************

.SUFFIXES: .$(cppSrcSuf) .$(forSrcSuf)


.$(cppSrcSuf).$(ObjSuf):
	$(CPP) $(CPPFLAGS) -c $<
.$(forSrcSuf).$(ObjSuf):
	$(FC) $(FFLAGS) -c $<

#*********************  DECLARING DEPENDENCIES ****************************************

nuf.$(ObjSuf): 	$(INCDIR)/nuf.h
cmdoptions.${ObjSuf} : 	$(INCDIR)/nuf.h
sdrunclass.${ObjSuf} : 	$(INCDIR)/nuf.h
