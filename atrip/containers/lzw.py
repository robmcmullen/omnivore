import numpy as np
try:
    import unlzw
except ImportError:
    unlzw = None

from .. import errors
from ..container import Container


class ZLibContainer(Container):
    """NOTE: this is the unix compress"""
    compression_algorithm = "lzw"

    def calc_unpacked_bytes(self, byte_data):
        if unlzw is None:
            raise errors.InvalidContainer("unlzw module needed for unix compress (.Z) support")
        try:
            unpacked = unlzw.unlzw(bytes(byte_data))
        except ValueError as e:
            raise errors.InvalidContainer(e)
        return unpacked
