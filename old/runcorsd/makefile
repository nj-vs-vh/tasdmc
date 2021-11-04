# to compile CORSIKA De-thinning and SD tile file production programs
SHELL    =/bin/bash

$(if $(wildcard $(DSTDIR)),,\
        $(error DSTDIR ($(DSTDIR)) not found))

$(if $(wildcard $(RUNCORSD_BINDIR)),,\
        $(warning RUNCORSD_BINDIR ($(RUNCORSD_BINDIR)) not found, using currect directory))

$(if $(wildcard $(RUNCORSD_BINDIR)),,\
	$(eval RUNCORSD_BINDIR=$(shell readlink -f $(shell pwd))))

INCS = -I$(DSTDIR)/inc
LIBS=-L$(DSTDIR)/lib -ldst2k -lm  -lc -lz -lbz2

# optimization flag; default is -O3
ifeq (x$(OPTOPT),x)
OPTOPT = -O3
endif

# 32 or 64 bit ?
chk32bit=$(shell uname -a | grep i686)

# default is gcc, ar for making libraries
CPP           = g++
CPPFLAGS      = $(OPTOPT) -Wall -fPIC
CC            = gcc
CFLAGS        = $(OPTOPT) -Wall -fPIC
LD            = g++
LDFLAGS       = $(OPTOPT)
AR            = ar
compiler_suf=gcc_x86
ifneq (x$(chk32bit),x)
compiler_suf=gcc_i686
endif

# intel compilers
ifneq (x$(usingicc),x)
CPP           = icpc
CPPFLAGS      = $(OPTOPT) -ipo -no-prec-div -xHost -fpic
CC            = icc
CFLAGS        = $(OPTOPT) -ipo -no-prec-div -xHost -fpic
LD            = icpc
LDFLAGS       = $(OPTOPT)
AR            = xiar
compiler_suf=icc
ifeq ($(UUFSCELL),kingspeak.peaks)
compiler_suf:=$(compiler_suf)_kp
endif
ifeq ($(UUFSCELL),ember.arches)
compiler_suf:=$(compiler_suf)_emb
endif
ifeq ($(UUFSCELL),ash.peaks)
compiler_suf:=$(compiler_suf)_ash
endif
ifeq ($(UUFSCELL),lonepeak.peaks)
compiler_suf:=$(compiler_suf)_lnp
endif
endif

# if running on a 32 bit machine, make adjustments to compiler flags so that programs can read
# large files
ifneq (x$(chk32bit),x)
CPPFLAGS      := $(CPPFLAGS) -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE
CFLAGS        := $(CFLAGS) -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE
endif

LINKLIST  = deweight
LINKLIST += corsika_split-th
LINKLIST += corsika2geant_2g
# on some platforms corsika2geant_4g can't be compiled
# due to large array allocations
#LINKLIST += corsika2geant_4g
LINKLIST += check_gea_dat_file
RUNCORSD_LINKS = $(addprefix ${RUNCORSD_BINDIR}/, ${LINKLIST})
RUNCORSD_BINS  = $(addsuffix _${compiler_suf}.run, ${RUNCORSD_LINKS})


.PHONY: all clean

all: ${RUNCORSD_LINKS}


${RUNCORSD_LINKS}: % : %_${compiler_suf}.run ; \
ln -fs $^ $@

clean: ; \
rm -f ${RUNCORSD_LINKS} ${RUNCORSD_BINS} *.o

$(RUNCORSD_BINDIR)/deweight_$(compiler_suf).run: deweight.o corsika_weights.o atmos_conv.o; \
$(CC) ${CFLAGS} ${INCS} -o $@ $^ ${LIBS}
$(RUNCORSD_BINDIR)/corsika_split-th_$(compiler_suf).run: corsika_split-th.o ; \
$(CC) ${CFLAGS} ${INCS} -o $@ $^ ${LIBS}
$(RUNCORSD_BINDIR)/corsika2geant_2g_$(compiler_suf).run: corsika2geant_2g_$(compiler_suf).o corsika_vem_2g_$(compiler_suf).o corsika_vem_init_2g_$(compiler_suf).o corsika_times_2g_$(compiler_suf).o eloss_sdgeant_2g_$(compiler_suf).o ; \
$(CC) ${CFLAGS} ${INCS} -o $@ $^ ${LIBS}
$(RUNCORSD_BINDIR)/corsika2geant_4g_$(compiler_suf).run: corsika2geant_4g_$(compiler_suf).o corsika_vem_4g_$(compiler_suf).o corsika_vem_init_4g_$(compiler_suf).o corsika_times_4g_$(compiler_suf).o eloss_sdgeant_4g_$(compiler_suf).o ; \
$(CC) ${CFLAGS} ${INCS} -o $@ $^ ${LIBS}
$(RUNCORSD_BINDIR)/check_gea_dat_file_$(compiler_suf).run: check_gea_dat_file.o; \
$(CPP) ${CPPFLAGS} ${INCS} -o $@ $^



########################### USEFUL SUFFIX RULES #########################

%.o : %.cpp ; \
$(CPP) $(CPPFLAGS) $(INCS) -o $@ $< -c

%.o : %.cxx ; \
$(CPP) $(CPPFLAGS) $(INCS) -o $@ $< -c

%.o : %.c ; \
$(CC) $(CFLAGS) $(INCS) -o $@ $< -c

%_2g_$(compiler_suf).o : %.c ; \
$(CC) -DNT=32 $(CFLAGS) $(INCS) -o $@ $< -c

%_4g_$(compiler_suf).o : %.c ; \
$(CC) -DNT=64 $(CFLAGS) $(INCS) -o $@ $< -c
