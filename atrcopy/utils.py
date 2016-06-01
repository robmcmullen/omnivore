import types

import numpy as np


def to_numpy(value):
    if type(value) is np.ndarray:
        return value
    elif type(value) is types.StringType:
        return np.fromstring(value, dtype=np.uint8)
    elif type(value) is types.ListType:
    	return np.asarray(value, dtype=np.uint8)
    raise TypeError("Can't convert to numpy data")


def to_numpy_list(value):
    if type(value) is np.ndarray:
        return value
    return np.asarray(value, dtype=np.uint32)
