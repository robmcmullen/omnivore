import zlib
import io

import numpy as np

from .. import errors
from ..container import Container


class ZLibContainer(Container):
    """NOTE: this is the GNU zip compression, not unix compress"""
    compression_algorithm = "zlib"

    def calc_unpacked_bytes(self, byte_data):
        try:
            unpacked = zlib.decompress(bytes(byte_data))
        except zlib.error as e:
            raise errors.InvalidContainer(e)
        return unpacked
