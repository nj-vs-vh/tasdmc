# if you have just cloned tasdmc repo, sdanalysis submodule is empty
# use this script to set it up to track main branch from sdanalysis repo

git submodule update --init --recursive --rebase
cd src/sdanalysis
git checkout main
cd ../..
