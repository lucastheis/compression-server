#!/bin/bash

docker run \
	-v "$(pwd)":"$(pwd)" \
	-w "$(pwd)" \
	gcr.io/clic-215616/submit \
	--use_gpu \
	-n "TFGPU" \
	-p "clic2019" \
	-e clic@compression.cc \
	decoder.py \
	images/*.jpg
