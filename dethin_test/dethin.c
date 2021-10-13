#include "../src/extensions/dethinning/main.h"

#define SAMPLE_THINNED_PARTICLE_FILE "/home/njvh/Documents/Science/ta/tasdmc/runs/test-run/corsika_output/DAT000085.p01"

#define OUTPUT_FILE "dethinning-out-buf"

int main() {
    dethinning(SAMPLE_THINNED_PARTICLE_FILE, "", OUTPUT_FILE, false);
}
