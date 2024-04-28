FROM postgres:14-bookworm

RUN apt update -y && apt install -y postgresql-contrib
COPY ./docker/postgres/docker-entrypoint-initdb.d /
