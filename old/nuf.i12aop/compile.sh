#!/bin/sh

targetname=$1

if [ -z $targetname ] ; then
  targetname=all
fi

cd src
make $targetname