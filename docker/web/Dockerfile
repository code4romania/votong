FROM python:3.11.8-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget nginx gcc xz-utils build-essential postgresql-client libpq-dev libffi-dev zlib1g-dev \
        gettext git gcc g++ && \
        python3 -m pip install --upgrade pip setuptools cython
    

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && chown root:root /usr/local/bin/dockerize

WORKDIR /opt/

ARG ENVIRONMENT=dev

ENV ENVIRONMENT=${ENVIRONMENT}
ENV DJANGO_SETTINGS_MODULE=civil_society_vote.settings.${ENVIRONMENT}

# Copy just the requirements for caching
COPY ./requirements*.txt /opt/
RUN pip install -r requirements-${ENVIRONMENT}.txt

WORKDIR /opt/civil_society_vote/

COPY ./docker/web/docker-entrypoint /
COPY ./ /opt/

ENTRYPOINT ["/docker-entrypoint"]
EXPOSE 8010
