import gzip
import bz2
import lzma
import io

import numpy as np

from . import errors
from .segments import SegmentData
from .utils import to_numpy


class DiskImageContainer:
    """Unpacker for disk image compression.

    Disk images may be compressed by any number of techniques. Subclasses of
    DiskImageContainer implement the `unpack_bytes` method which examines the
    byte_data argument for the supported compression type, and if valid returns
    the unpacked bytes to be used in the disk image parsing.
    """
    def __init__(self, data):
        self.unpacked = self.__unpack_raw_data(data)

    def __unpack_raw_data(self, data):
        raw = data.tobytes()
        try:
            unpacked = self.unpack_bytes(raw)
        except EOFError as e:
            raise errors.InvalidContainer(e)
        return to_numpy(unpacked)

    def unpack_bytes(self, byte_data):
        """Attempt to unpack `byte_data` using this unpacking algorithm.

        `byte_data` is a byte string, and should return a byte string if
        successfully unpacked. Conversion to a numpy array will take place
        automatically, outside of this method.

        If the data is not recognized by this subclass, raise an
        InvalidContainer exception. This signals to the caller that a different
        container type should be tried.

        If the data is recognized by this subclass but the unpacking algorithm
        is not implemented, raise an UnsupportedContainer exception. This is
        different than the InvalidContainer exception because it indicates that
        the data was indeed recognized by this subclass (despite not being
        unpacked) and checking further containers is not necessary.
        """
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


class BZipContainer(DiskImageContainer):
    def unpack_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with bz2.BZ2File(buf, mode='rb') as f:
                unpacked = f.read()
        except OSError as e:
            raise errors.InvalidContainer(e)
        return unpacked


class LZMAContainer(DiskImageContainer):
    def unpack_bytes(self, byte_data):
        try:
            buf = io.BytesIO(byte_data)
            with lzma.LZMAFile(buf, mode='rb') as f:
                unpacked = f.read()
        except lzma.LZMAError as e:
            raise errors.InvalidContainer(e)
        return unpacked
