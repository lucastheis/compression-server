#!/bin/bash

docker run \
	-v "$(pwd)":"$(pwd)" \
	-w "$(pwd)" \
	-e "EVAL_SERVER=35.190.138.93" \
	gcr.io/clic-215616/submit \
	-n "JPEG420" \
	-p "clic2019" \
	-e clic@compression.cc \
	decoder.py \
	images/*.jpg
