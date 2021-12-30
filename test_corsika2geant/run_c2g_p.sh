for DETHIN in *.dethinned
do
    corsika2geant_parallel_process.run $DETHIN ../data/sdgeant.dst $DETHIN.tile
    # break;
done
