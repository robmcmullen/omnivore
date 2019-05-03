import numpy as np
try:
    import unlzw
except ImportError:
    unlzw = None

from .. import errors
from ..compressor import Compressor


class ZLibCompressor(Compressor):
    """NOTE: this is the unix compress"""
    compression_algorithm = "lzw"

    def calc_unpacked_data(self, byte_data):
        if unlzw is None:
            raise errors.InvalidCompressor("unlzw module needed for unix compress (.Z) support")
        try:
            unpacked = unlzw.unlzw(bytes(byte_data))
        except ValueError as e:
            raise errors.InvalidCompressor(e)
        return unpacked
