import subprocess
import argparse
import sys
import os
import numpy as np
import tempfile
from PIL import Image


_BUTTERAUGLI_BIN = os.environ.get('BUTTERAUGLI_BIN', './butteraugli')


# check if binary exists ---
def _check_bin():
    if not os.path.isfile(_BUTTERAUGLI_BIN):
        return False
    else:
        try:
            # Python 3.3+
            otp = subprocess.run(_BUTTERAUGLI_BIN, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
            return otp == 1  # default return code of butteraugli w/o args
        except PermissionError as e:
            print(e)
            return False


if not _check_bin():
    print('butteraugli binary not available or executable: `{}`. Make sure it is available in $PATH or at '
          '$BUTTERAUGLI_BIN.'.format(_BUTTERAUGLI_BIN))
    sys.exit(1)
# ---------------


def _normalize(img, max_val, auto_transpose):
    if img.dtype == np.float32:
        if max_val is None:
            raise ValueError('Input is float32. Expected max_val.')
        img = (img / max_val * 255.).round().astype(np.uint8)
    if img.dtype != np.uint8:
        raise ValueError('Expected uint8 or float32, got {}, {}'.format(img.dtype, img.dtype))
    shape = img.shape
    if len(shape) != 3:
        raise ValueError('Expected HWC or CHW, got shape {}'.format(shape))
    if shape[-1] == 3:
        return img
    if shape[0] == 3:
        if auto_transpose:
            return img.transpose(1, 2, 0)
        else:
            raise ValueError('Got 3HW, pass either HW3 or use auto_transpose=True (shape: {})'.format(shape))

    raise ValueError('Invalid, expected C=3 channels, got shape {}'.format(shape))


def compare_image_numpy(imga, imgb, max_val=None, auto_transpose=False):
    """
    Compare numpy images.
    For the numpy arrays it is expected:
        - shape: HW3 (or 3HW if auto_transpose = True)
        - dtype: uint8 or np.float32 (which requires max_val to be set)
    :param imga: Numpy array
    :param imgb: Numpy array
    :param max_val: float or None: If given, input arrays are assumed to contain values in [0, max_val] and will be
    rescaled to {0, ..., 255} uint8s
    :param auto_transpose: If given, transpose 3HW to HW3
    :return: butteraugli score
    """
    if imga.shape != imgb.shape:
        raise ValueError('Expected equal shapes: {}, {}'.format(imga.shape, imgb.shape))
    imga = _normalize(imga, max_val, auto_transpose)
    imgb = _normalize(imgb, max_val, auto_transpose)

    with tempfile.TemporaryDirectory() as tmp:
        imga_p = os.path.join(tmp, '_a.png')
        imgb_p = os.path.join(tmp, '_b.png')
        Image.fromarray(imga).save(imga_p)
        Image.fromarray(imgb).save(imgb_p)
        v = compare_image_paths(imga_p, imgb_p)
    return v


def compare_image_paths(imga_p, imgb_p):
    """
    :param imga_p: path of first image
    :param imgb_p: path of second image
    :return: butteraugli score
    """
    if not os.path.isfile(imga_p) or not os.path.isfile(imgb_p):
        raise ValueError('Files not available: {} and/or {}'.format(imga_p, imgb_p))
    return float(subprocess.check_output([_BUTTERAUGLI_BIN, imga_p, imgb_p]).decode().strip())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('imga_path')
    p.add_argument('imgb_path')
    flags = p.parse_args()
    score = compare_image_paths(flags.imga_path, flags.imgb_path)
    print(score)
    


if __name__ == '__main__':
    main()






