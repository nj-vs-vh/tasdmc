SHELL=/bin/bash

# config and prerequisites

OPTIMIZATION_OPTION = -O3
CC                  = gcc
CFLAGS              = $(OPTIMIZATION_OPTION) -Wall -fPIC
CPP	                = g++
CPPFLAGS            = $(OPTIMIZATION_OPTION) -Wall -fPIC

SRC_TO_OBJ_RECIPE = ${CC} -c $< -o $@ ${CFLAGS}
OBJ_TO_SHARED_LIB_RECIPE = ${CC} -shared $^ -o $@ ${CFLAGS}
MKDIR_RECIPE = mkdir -p $@

envcheck:
ifeq ($(and ${TASDMC_LIB_DIR}, ${DST2K_DIR}, ${TASDMC_MEMORY_PER_PROCESS_GB}),)
	$(error Required environment variables are not defined! See README for details)
endif

BINDIR= ./bin
${BINDIR}: envcheck
	${MKDIR_RECIPE}


# dethinning (compiled statically from several source files then turned to shared lib)

DETHIN = dethinning

DETHBINDIR = ${BINDIR}/${DETHIN}
${DETHBINDIR}: | ${BINDIR}
	${MKDIR_RECIPE}

# ${BINDIR}/${DETHIN}.o: ${DETHBINDIR}/main.o ${DETHBINDIR}/atmosphere.o ${DETHBINDIR}/corsika_weights.o | ${DETHBINDIR}
# 	ld -r -o $@ $^

DETHIN_OBJS = $(addsuffix .o, $(addprefix ${DETHBINDIR}/, main corsika_weights atmosphere))

${BINDIR}/lib${DETHIN}.so: ${DETHIN_OBJS} | ${DETHBINDIR}
	${OBJ_TO_SHARED_LIB_RECIPE}


# corsika2geant should be linked with dst2k-ta/include code

C2G = corsika2geant

C2GBINDIR = ${BINDIR}/${C2G}
${C2GBINDIR}: | ${BINDIR}
	${MKDIR_RECIPE}

C2G_OBJS = $(addsuffix .o, $(addprefix ${C2GBINDIR}/, main corsika_times corsika_vem_init corsika_vem eloss_sdgeant))

# calculating 16 * (memory in Gb) with bc & deleting everything after decimal point from output
NT_VALUE := $(shell echo "16 * ${TASDMC_MEMORY_PER_PROCESS_GB}" | bc | cut -d '.' -f 1)
WITH_DEFINED_NT = -DNT=${NT_VALUE}
WITH_LINK_TO_DST2K = -I${DST2K_DIR}/inc -L$(DST2K_DIR)/lib -L/usr/lib/x86_64-linux-gnu -ldst2k -lm  -lc -lz -lbz2

${C2GBINDIR}/%.o: ${C2G}/%.c
	${SRC_TO_OBJ_RECIPE} ${WITH_DEFINED_NT} ${WITH_LINK_TO_DST2K}

${BINDIR}/lib${C2G}.so: ${C2G_OBJS} | ${C2GBINDIR}
	${OBJ_TO_SHARED_LIB_RECIPE} ${WITH_LINK_TO_DST2K}


# lists of targets

DIRS = ${BINDIR} ${DETHBINDIR} ${C2GBINDIR}

STEMS = corsika_split_th ${DETHIN} ${C2G}

LIB_FILES = $(addprefix lib, $(addsuffix .so, ${STEMS}))

LIB_PATHS = $(addprefix ${BINDIR}/, ${LIB_FILES})


# commands

.PHONY: install clean reinstall

install: ${LIB_PATHS}
	mkdir -p ${TASDMC_LIB_DIR} && \
	cp ${LIB_PATHS} ${TASDMC_LIB_DIR}

clean:
	rm -rf ${BINDIR} && \
	cd ${TASDMC_LIB_DIR} && rm ${LIB_FILES}

reinstall: clean | install


# pattern rules

${BINDIR}/%.o: %.c | ${DIRS}
	${SRC_TO_OBJ_RECIPE}

${BINDIR}/lib%.so: ${BINDIR}/%.o
	${OBJ_TO_SHARED_LIB_RECIPE}
