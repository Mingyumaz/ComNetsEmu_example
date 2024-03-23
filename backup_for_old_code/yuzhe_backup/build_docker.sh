#! /bin/bash


echo "The built simple_dev image is large (around 3GB). "

echo "Build docker images for simple object detection..."
# --squash: Squash newly built layers into a single new layer
# Used to reduce built image size.

sudo docker build -t simple_dev:1.0 -f ./Dockerfile.dev .
sudo docker image prune --force