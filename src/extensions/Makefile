# config and prerequisites

OPTIMIZATION_OPTION	= -O3
CC					= gcc
CFLAGS				= $(OPTIMIZATION_OPTION) -Wall -fPIC
CPP					= g++
CPPFLAGS			= $(OPTIMIZATION_OPTION) -Wall -fPIC

envcheck:
ifndef TASDMC_LIB_DIR
	$(error TASDMC_LIB_DIR is not defined)
endif

BINDIR= ./bin
${BINDIR}: envcheck
	mkdir -p ${BINDIR}


# list of target file stems w/ lib filenames and targets (with ./bin/target)

SRC = corsika_split_th
SRC += dummy

LIB_FILES = $(addsuffix .so, $(addprefix lib, ${SRC}))

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

${BINDIR}/%.o: %.c | ${BINDIR}
	${CC} -c $< -o $@ ${CFLAGS}

${BINDIR}/lib%.so: ${BINDIR}/%.o
	${CC} -shared $< -o $@ ${CFLAGS}
