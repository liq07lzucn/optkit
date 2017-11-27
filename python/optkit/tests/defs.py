from optkit.compat import *

import os
import numpy as np
import unittest

TEST_ITERATE = int(os.getenv('OPTKIT_REPEAT_NUMERICALTEST', '0'))
VERBOSE_TEST = os.getenv('OPTKIT_TEST_VERBOSE', False)
LIB_CONDITIONS = [(a, b) for a in (True, False) for b in (True, False)]

DEFAULT_SHAPE = (500, 800)
# DEFAULT_SHAPE = (10, 15)

# todo: modify test code to use env specified test conditions if availabe
DEFAULT_ROWS = os.getenv('OPTKIT_TESTING_DEFAULT_NROWS', None)
DEFAULT_COLS = os.getenv('OPTKIT_TESTING_DEFAULT_NCOLS', None)
DEFAULT_MATRIX_PATH = os.getenv('OPTKIT_TESTING_DEFAULT_MATRIX', None)
DEFAULT_SPARSE_OCCUPANCY = os.getenv('OPTKIT_TESTING_DEFAULT_SPARSE_OCCUPANCY',
                                  0.4)

if DEFAULT_MATRIX_PATH is not None:
    if not os.path.exsists(DEFAULT_MATRIX_PATH):
        DEFAULT_MATRIX_PATH = None
    elif not DEFAULT_MATRIX_PATH.endswith('.npy'):
        DEFAULT_MATRIX_PATH = None

DEFAULT_MATRIX = None
if DEFAULT_MATRIX_PATH is not None:
    try:
        DEFAULT_MATRIX = np.load(DEFAULT_MATRIX_PATH)
    except:
        pass

if DEFAULT_ROWS is not None:
    try:
        DEFAULT_ROWS = int(DEFAULT_ROWS)
    except:
        DEFAULT_ROWS = None
if DEFAULT_COLS is not None:
    try:
        DEFAULT_COLS = int(DEFAULT_COLS)
    except:
        DEFAULT_COLS = None

if DEFAULT_ROWS is not None:
    DEFAULT_SHAPE = (DEFAULT_ROWS, DEFAULT_SHAPE[1])
if DEFAULT_COLS is not None:
    DEFAULT_SHAPE = (DEFAULT_SHAPE[0], DEFAULT_COLS)

def A_test_gen():
    if DEFAULT_MATRIX is not None:
        return DEFAULT_MATRIX
    else:
        return np.random.rand(*DEFAULT_SHAPE)

def shape():
    if DEFAULT_MATRIX is not None:
        return DEFAULT_MATRIX.shape
    else:
        return DEFAULT_SHAPE

def A_test_sparse_gen():
    A_ = DEFAULT_MATRIX if DEFAULT_MATRIX else np.random.rand(*DEFAULT_SHAPE)
    mask = np.random.rand(*A_.shape) < DEFAULT_SPARSE_OCCUPANCY
    self.__nnz = sum(sum(mask))
    return A_ * mask

def version_string(major, minor, change, status):
    v = '{}.{}.{}'.format(major, minor, change)
    if status:
        v.join('-{}'.format(chr(status)))
    return v


class OptkitTestCase(unittest.TestCase):
    VERBOSE_TEST = os.getenv('OPTKIT_TEST_VERBOSE', False)

    # library conditions: gpu = True/False, single_precision = True/False
    CONDITIONS = [(a, b) for a in (True, False) for b in (True, False)]

    __nnz = 0

    @property
    def nnz(self):
        return self.__nnz

    @property
    def shape(self):
        if DEFAULT_MATRIX is not None:
            return DEFAULT_MATRIX.shape
        else:
            return DEFAULT_SHAPE

    @property
    def A_test_gen(self):
        if DEFAULT_MATRIX is not None:
            return DEFAULT_MATRIX
        else:
            return np.random.rand(*self.shape)

    @property
    def A_test_sparse_gen(self):
        A_ = DEFAULT_MATRIX if DEFAULT_MATRIX else np.random.rand(*self.shape)
        mask = np.random.rand(*self.shape) < DEFAULT_SPARSE_OCCUPANCY
        self.__nnz = sum(sum(mask))
        return A_ * mask

    @staticmethod
    def version_string(major, minor, change, status):
        v = '{}.{}.{}'.format(major, minor, change)
        if status:
            v.join('-{}'.format(chr(status)))
        return v