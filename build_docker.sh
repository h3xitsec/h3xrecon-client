#!/usr/bin/env bash

python -m hatchling build && \
docker build -t ghcr.io/h3xitsec/h3xrecon/client:dev -f ./Dockerfile .