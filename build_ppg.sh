#!/bin/sh

if [ ! -d planpro-generator ]
then
    git clone https://github.com/ctiedt/planpro-generator
fi
cd planpro-generator
git pull
ant

cp ppg.jar ..