import zlib
import io

import numpy as np

from .. import errors
from ..compressor import Compressor


class ZLibCompressor(Compressor):
    """NOTE: this is the GNU zip compression, not unix compress"""
    compression_algorithm = "zlib"

    def calc_unpacked_data(self, byte_data):
        try:
            unpacked = zlib.decompress(bytes(byte_data))
        except zlib.error as e:
            raise errors.InvalidAlgorithm(e)
        return unpacked

    def calc_packed_data(self, byte_data, media=None):
        try:
            packed = zlib.compress(bytes(byte_data), 9)
        except zlib.error as e:
            raise errors.InvalidAlgorithm(e)
        return packed
