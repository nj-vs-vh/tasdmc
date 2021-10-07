# general compilation config
CC = gcc
CFLAGS = -g -O3 -std=gnu11

BINDIR= ./bin
${BINDIR}:
	mkdir -p ${BINDIR}


# split corsika thinned routine
COR_SPLIT_TH_OBJECT = ${BINDIR}/corsika_split_th.o
COR_SPLIT_TH_LIB = ${BINDIR}/libcorsika_split_th.so
${COR_SPLIT_TH_OBJECT}: corsika_split_th.c | ${BINDIR}
	${CC} -c -fPIC $< -o $@ ${CFLAGS}
${COR_SPLIT_TH_LIB}: ${COR_SPLIT_TH_OBJECT} | ${BINDIR}
	${CC} -shared $< -o $@ ${CFLAGS}

ALL_LIBS = $(notdir ${COR_SPLIT_TH_LIB})

.PHONY: install clean reinstall

install: ${COR_SPLIT_TH_LIB}
	mkdir -p ${TASDMC_LIB_DIR} && \
	cp ${COR_SPLIT_TH_LIB} ${TASDMC_LIB_DIR}

clean:
	rm -rf ${BINDIR} && \
	cd ${TASDMC_LIB_DIR} && rm ${ALL_LIBS}

reinstall: clean | install
