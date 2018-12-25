#!/bin/bash

for f in ~/Downloads/valid*/*.png; do
	convert "$f" -sampling-factor "4:2:0" -quality 7 "images/$(basename ${f/.png/.jpg})";
done
