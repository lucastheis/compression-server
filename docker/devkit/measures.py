import numpy as np
import tensorflow as tf
from msssim import MultiScaleSSIM


# MSE --------------------


def np_mse(img_a, img_b):
    """
    :param img_a: First image, as numpy array
    :param img_b: Second image, as numpy array
    :return: MSE between images
    """
    return np.mean(np.square(img_b - img_a))


def tf_mse(img_a, img_b, name='mse'):
    """
    :param img_a: First image, as TensorFlow tensor
    :param img_b: Second image, as TensorFlow tensor
    :return: MSE between images
    """
    with tf.name_scope(name):
        return tf.reduce_mean(tf.square(img_b - img_a))


# PSNR --------------------


def np_psnr(img_a, img_b, max_val):
    """
    :param img_a: First image, as numpy array
    :param img_b: Second image, as numpy array
    :param max_val: Maximum value that an image can have, e.g., 255. or 1., depending on normalization
    :return: PSNR between images
    """
    return 10. * np.log10((max_val ** 2) / np_mse(img_a, img_b))


def tf_psnr(img_a, img_b, max_val, name='psnr'):
    """
    :param img_a: First image, as TensorFlow tensor
    :param img_b: Second image, as TensorFlow tensor
    :param max_val: Maximum value that an image can have, e.g., 255. or 1., depending on normalization
    :param name: Name to use for TF
    :return: PSNR between images
    """
    with tf.name_scope(name):
        return 10. * tf.log((max_val ** 2) / tf_mse(img_a, img_b)) / tf.log(10.)


# MS-SSIM --------------------


def np_msssim(img_a, img_b, max_val):
    """
    :param img_a: First image, as numpy array
    :param img_b: Second image, as numpy array
    :param max_val: Maximum value that an image can have, e.g., 255. or 1., depending on normalization
    :return: MS-SSIM between images
    """
    return MultiScaleSSIM(img_a, img_b, max_val)


def tf_msssim(img_a, img_b, max_val):
    """
    :param img_a: First image, as TensorFlow tensor
    :param img_b: Second image, as TensorFlow tensor
    :param max_val: Maximum value that an image can have, e.g., 255. or 1., depending on normalization
    :return: MS-SSIM between images
    """
    return tf.image.ssim_multiscale(img_a, img_b, max_val)
