SHELL=/bin/bash

envcheck:
ifeq ($(and ${TASDMC_BIN_DIR}, ${SDANALYSIS_DIR}, ${TASDMC_MEMORY_PER_PROCESS_GB}),)
	$(error Required environment variables are not defined! See README for details)
endif

# config and prerequisites

OPTIMIZATION_OPTION = -O3
CC                  = gcc
CFLAGS              = $(OPTIMIZATION_OPTION) -Wall -fPIC
CPP	                = g++
CPPFLAGS            = $(OPTIMIZATION_OPTION) -Wall -fPIC

INCS = -I${SDANALYSIS_DIR}/dst2k-ta/inc
LIBS=-L${SDANALYSIS_DIR}/dst2k-ta/lib -ldst2k -lm  -lc -lz -lbz2

SRC_TO_OBJ_RECIPE = ${CC} -c $< -o $@ ${CFLAGS} ${INCS}
OBJ_TO_EXECUTABLE_RECIPE = ${CC} $^ -o $@ ${CFLAGS} ${LIBS}
MKDIR_RECIPE = mkdir -p $@

BINDIR= ./bin
${BINDIR}: envcheck
	${MKDIR_RECIPE}


# dethinning

DETHIN = dethinning

DETHBINDIR = ${BINDIR}/${DETHIN}
${DETHBINDIR}: | ${BINDIR}
	${MKDIR_RECIPE}

# ${BINDIR}/${DETHIN}.o: ${DETHBINDIR}/main.o ${DETHBINDIR}/atmosphere.o ${DETHBINDIR}/corsika_weights.o | ${DETHBINDIR}
# 	ld -r -o $@ $^

DETHIN_OBJS = $(addsuffix .o, $(addprefix ${DETHBINDIR}/, main corsika_weights atmosphere))

${BINDIR}/${DETHIN}.run: ${DETHIN_OBJS} | ${DETHBINDIR}
	${OBJ_TO_EXECUTABLE_RECIPE}


# corsika2geant

C2G = corsika2geant

C2GBINDIR = ${BINDIR}/${C2G}
${C2GBINDIR}: | ${BINDIR}
	${MKDIR_RECIPE}

C2G_OBJS = $(addsuffix .o, $(addprefix ${C2GBINDIR}/, main corsika_times corsika_vem_init corsika_vem eloss_sdgeant))

# calculating 16 * (memory in Gb) with bc & deleting everything after decimal point from output
NT_VALUE := $(shell echo "16 * ${TASDMC_MEMORY_PER_PROCESS_GB}" | bc | cut -d '.' -f 1)
WITH_DEFINED_NT = -DNT=${NT_VALUE}

${C2GBINDIR}/%.o: ${C2G}/%.c
	${SRC_TO_OBJ_RECIPE} ${WITH_DEFINED_NT}

${BINDIR}/${C2G}.run: ${C2G_OBJS} | ${C2GBINDIR}
	${OBJ_TO_EXECUTABLE_RECIPE}


# corsika2geant_parallel

C2G_P = corsika2geant_parallel

C2G_PBINDIR = ${BINDIR}/${C2G_P}
${C2G_PBINDIR}: | ${BINDIR}
	${MKDIR_RECIPE}

C2G_P_OBJS = $(addsuffix .o, $(addprefix ${C2G_PBINDIR}/, main corsika_vem_init corsika_vem eloss_sdgeant iterator structs))

# calculating 16 * (memory in Gb) with bc & deleting everything after decimal point from output
NT_VALUE := $(shell echo "16 * ${TASDMC_MEMORY_PER_PROCESS_GB}" | bc | cut -d '.' -f 1)
WITH_DEFINED_NT = -DNT=${NT_VALUE}

${C2G_PBINDIR}/%.o: ${C2G_P}/%.c
	${SRC_TO_OBJ_RECIPE} ${WITH_DEFINED_NT}

${BINDIR}/${C2G_P}.run: ${C2G_P_OBJS} | ${C2G_PBINDIR}
	${OBJ_TO_EXECUTABLE_RECIPE}


# lists of targets

DIRS = ${BINDIR} ${DETHBINDIR} ${C2GBINDIR} ${C2G_PBINDIR}

STEMS = corsika_split_th check_gea_dat_file ${DETHIN} ${C2G} ${C2G_P}

EXECUTABLES = $(addsuffix .run, ${STEMS})

EXECUTABLE_PATHS = $(addprefix ${BINDIR}/, ${EXECUTABLES})


# commands

.PHONY: install clean reinstall

install: ${EXECUTABLE_PATHS}
	mkdir -p ${TASDMC_BIN_DIR} && \
	cp ${EXECUTABLE_PATHS} ${TASDMC_BIN_DIR}

clean:
	rm -rf ${BINDIR} && \
	cd ${TASDMC_BIN_DIR} && \
	rm ${EXECUTABLES}

reinstall: clean | install


# pattern rules

${BINDIR}/%.o: %.c | ${DIRS}
	${SRC_TO_OBJ_RECIPE}

${BINDIR}/%.run: ${BINDIR}/%.o
	${OBJ_TO_EXECUTABLE_RECIPE}
