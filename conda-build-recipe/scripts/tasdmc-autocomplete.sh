# activation script, executed on user system during env activation

tasdmc >/dev/null 2>/dev/null  # testing if tasdmc is actually runable

if [ $? -eq 0 ] && [ "$BASH_VERSION" > "4.4" ]
then
    eval "$(_TASDMC_COMPLETE=bash_source tasdmc)"
fi
