import lzma
import io

import numpy as np

from . import errors
from .utils import to_numpy


class LZMAContainer(DiskImageContainer):
    def unpack_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with lzma.LZMAFile(buf, mode='rb') as f:
                unpacked = f.read()
        except lzma.LZMAError as e:
            raise errors.InvalidContainer(e)
        return unpacked
