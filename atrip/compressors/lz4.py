import numpy as np
try:
    import lz4.frame as lz4
except ImportError:
    lz4 = None

from .. import errors
from ..compressor import Compressor


class LZ4Compressor(Compressor):
    compression_algorithm = "lz4"

    def calc_unpacked_data(self, byte_data):
        if lz4 is None:
            raise errors.InvalidAlgorithm("lz4 module needed for .lz4 support")
        try:
            unpacked = lz4.decompress(bytes(byte_data))
        except RuntimeError as e:
            raise errors.InvalidAlgorithm(e)
        return unpacked

    def calc_packed_data(self, byte_data, media=None):
        if lz4 is None:
            raise errors.InvalidAlgorithm("lz4 module needed for .lz4 support")
        try:
            packed = lz4.compress(bytes(byte_data))
        except RuntimeError as e:
            raise errors.InvalidAlgorithm(e)
        return packed
