#! /usr/bin/env sh 
set -x
cd $VOTONG_HOME
git pull
docker-compose down
docker-compose build
docker-compose up -d
