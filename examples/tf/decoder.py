#!/usr/bin/env python2

import os

import numpy as np
import tensorflow as tf

from glob import glob
from PIL import Image

# kernel rescales pixel values to [0, 255]
scaling = np.ones([5, 5, 3, 3], dtype=np.float32)
scaling[2, 2, 0, 0] = 255.
scaling[2, 2, 1, 1] = 255.
scaling[2, 2, 2, 2] = 255.
kernel = tf.Variable(scaling)

# load image
image_path = tf.placeholder(tf.string)
image = tf.io.read_file(image_path)
image = tf.image.decode_image(image, dtype=tf.float32)

# rescale pixel values
images = tf.expand_dims(image, axis=0)
outputs = tf.nn.conv2d(images, kernel, [1, 1, 1, 1], 'SAME', data_format='NHWC')
output = tf.cast(tf.clip_by_value(outputs[0], 0., 255.), tf.uint8)

with tf.Session() as sess:
	# initialize kernel
	sess.run(tf.global_variables_initializer())

	# simply load and save images
	for file_path in glob('images/*.jpg'):
		print('Processing {0}'.format(file_path))
		image = sess.run(output, feed_dict={image_path: file_path})
		Image.fromarray(image, "RGB").save(
			os.path.splitext(os.path.basename(file_path))[0] + '.png')
