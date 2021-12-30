PTILELIST=partial_tile_list

rm $PTILELIST
touch $PTILELIST

for PTILE in *.dethinned.tile
do
    echo $PTILE >> $PTILELIST
    # break;
done

corsika2geant_parallel_merge.run $PTILELIST c2g_p_gea.dat
