#!/bin/sh
cd `pwd`/src
make clean
make ARG=$1 all 
