import gzip
import io

import numpy as np

from . import errors
from .segments import SegmentData
from .utils import to_numpy


class DiskImageContainer:
    def __init__(self, data):
        self.unpacked = self.__unpack_raw_data(data)

    def __unpack_raw_data(self, data):
        raw = data.tobytes()
        unpacked = self.unpack_bytes(raw)
        return to_numpy(unpacked)

    def unpack_bytes(self, byte_data):
        pass


class GZipContainer(DiskImageContainer):
    def unpack_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with gzip.GzipFile(mode='rb', fileobj=buf) as f:
                unpacked = f.read()
        except OSError as e:
            raise errors.InvalidContainer(e)
        return unpacked
