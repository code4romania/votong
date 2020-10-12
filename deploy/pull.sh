#! /usr/bin/env sh 
set -v
cd $VOTONG_HOME
git pull
docker-compose down
docker-compose build
docker-compose up -d
