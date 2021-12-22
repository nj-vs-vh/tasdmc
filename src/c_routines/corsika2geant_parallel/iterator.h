#include <stdbool.h>
#include "./constants.h"
#include "./structs.h"

// Iterator over CORSIKA output particle file, executing a callback on each particle
// returns success flag
bool iterateCorsikaParticleFile(
    const char *particle_filename,
    void (*processParticle)(ParticleData *, EventHeaderData *),
    ParticleFileStats *stats,
    EventHeaderData *event_header_data,
    bool verbose);

bool iteratePlainParticleFile(
    FILE *plain_particle_stream,
    void (*processParticle)(ParticleData *, EventHeaderData *),
    EventHeaderData *event_header_data);