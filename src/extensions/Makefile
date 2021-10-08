# config and prerequisites

OPTIMIZATION_OPTION	= -O3
CC					= gcc
CFLAGS				= $(OPTIMIZATION_OPTION) -Wall -fPIC
CPP					= g++
CPPFLAGS			= $(OPTIMIZATION_OPTION) -Wall -fPIC

SRC_TO_OBJ_RULE = ${CC} -c $< -o $@ ${CFLAGS}
OBJ_TO_SHARED_LIB_RULE = ${CC} -shared $< -o $@ ${CFLAGS}

envcheck:
ifndef TASDMC_LIB_DIR
	$(error TASDMC_LIB_DIR is not defined)
endif

BINDIR= ./bin
${BINDIR}: envcheck
	mkdir -p ${BINDIR}


# dethinning (compiled statically from several source files then turned to shared lib)

DETHBINDIR = ${BINDIR}/dethinning
${DETHBINDIR}: | ${BINDIR}
	mkdir -p ${DETHBINDIR}

DETHIN = dethinning

${BINDIR}/${DETHIN}.o: ${DETHBINDIR}/main.o ${DETHBINDIR}/atmosphere.o ${DETHBINDIR}/corsika_weights.o | ${DETHBINDIR}
	ld -r -o $@ $^


# list of target file stems
DIRS = ${BINDIR} ${DETHBINDIR}

SRC = corsika_split_th ${DETHIN}

LIB_FILES = $(addprefix lib, $(addsuffix .so, ${SRC}))

LIB_TARGETS = $(addprefix ${BINDIR}/, ${LIB_FILES})


# commands

.PHONY: install clean reinstall

install: ${LIB_TARGETS}
	mkdir -p ${TASDMC_LIB_DIR} && \
	cp ${LIB_TARGETS} ${TASDMC_LIB_DIR}

clean:
	rm -rf ${BINDIR} && \
	cd ${TASDMC_LIB_DIR} && rm ${LIB_FILES}

reinstall: clean | install


# pattern rules

${BINDIR}/%.o: %.c | ${DIRS}
	${SRC_TO_OBJ_RULE}

${BINDIR}/lib%.so: ${BINDIR}/%.o
	${OBJ_TO_SHARED_LIB_RULE}
