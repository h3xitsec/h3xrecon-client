#!/usr/bin/env bash

python -m hatchling build && \
# Extract the VERSION from __about__.py using grep with Perl regex
VERSION=$(grep -oP '(?<=__version__ = ").*(?=")' ./src/h3xrecon_client/__about__.py)

# Check if VERSION extraction was successful
if [[ -z "$VERSION" ]]; then
    echo "Failed to extract VERSION. Exiting."
    exit 1
fi

echo "Building client version ${VERSION}"

docker build -t ghcr.io/h3xitsec/h3xrecon/client:${VERSION} -f ./Dockerfile .
