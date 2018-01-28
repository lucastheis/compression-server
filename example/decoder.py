#!/usr/bin/env python3

from PIL import Image
from glob import glob

for image_file in glob('images/*.jpg'):
    Image.open(image_file).save(image_file[:-3] + 'png')
