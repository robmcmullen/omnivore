import bz2
import io

import numpy as np

from . import errors
from .utils import to_numpy


class BZipContainer(DiskImageContainer):
    def unpack_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with bz2.BZ2File(buf, mode='rb') as f:
                unpacked = f.read()
        except OSError as e:
            raise errors.InvalidContainer(e)
        return unpacked
