LISTFILE=dethinned_list

rm $LISTFILE
touch $LISTFILE

for dethinned in DAT000085.p??.dethinned
do
    echo $dethinned >> $LISTFILE
    # break;
done

corsika2geant.run $LISTFILE ../data/sdgeant.dst c2g_gea.dat

rm c2g_gea.dat.tmp???
