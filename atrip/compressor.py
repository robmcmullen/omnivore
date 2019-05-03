import os
import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .utils import to_numpy, to_numpy_list, uuid
from . import media_type
from . import filesystem

import logging
log = logging.getLogger(__name__)


class Compressor:
    """Compressor (packer/unpacker) for disk image compression.

    In their native data format, disk images may be stored as raw data or can
    be compressed by any number of techniques. Subclasses of Compressor
    implement the `calc_unpack_data` method which examines the byte_data
    argument for the supported compression type, and if valid returns the
    unpacked bytes to be used in the disk image parsing.

    Compressors are stateless, but are implemented as normal classes for
    convenience and ease of subclassing.
    """
    compression_algorithm = "none"

    def __init__(self, numpy_data):
        self.unpacked = self.calc_unpacked_data(numpy_data)

    @property
    def is_compressed(self):
        return self.compression_algorithm != Compressor.compression_algorithm

    #### decompression

    def calc_unpacked_data(self, numpy_data):
        """Attempt to unpack `numpy_data` using this unpacking algorithm.

        `numpy_data` must be a numpy array of `np.uint8` bytes.

        If the data is not recognized by this subclass, raise an
        `InvalidCompression` exception. The caller must recognize this and move
        on to trying the next compressor in the list.

        If the data is recognized by this subclass but the unpacking algorithm
        is not implemented, raise an `UnsupportedCompression` exception. This
        is different than the `InvalidCoCompression` exception because it
        indicates that the data was indeed recognized by this subclass (despite
        not being unpacked) and checking further compressors is not necessary.
        """
        if not self.is_compressed:
            return numpy_data
        else:
            raise errors.InvalidCompressor(f"Uncompressing '{self.compression_algorithm}' not implemented")

    #### compression

    def calc_packed_data(self, numpy_data):
        """Pack this data into a compressed data array using this packing
        algorithm.

        Subclasses should raise the `UnsupportedCompression` exception if
        compression is not implemented.
        """
        if not self.is_compressed:
            return numpy_data
        else:
            raise errors.UnsupportedCompressor(f"Compressing '{self.compression_algorithm}' not implemented")


_compressors = None

def _find_compressors():
    compressors = []
    for entry_point in pkg_resources.iter_entry_points('atrip.compressors'):
        mod = entry_point.load()
        log.debug(f"find_compressor: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and Compressor in obj.__mro__[1:]:
                log.debug(f"find_compressors:   found compressor class {name}")
                compressors.append(obj)
    return compressors

def find_compressors():
    global _compressors

    if _compressors is None:
        _compressors = _find_compressors()
    return _compressors

def guess_compressor(raw_data):
    compressor = None
    for c in find_compressors():
        log.debug(f"trying compressor {c.compression_algorithm}")
        try:
            compressor = c(raw_data)
        except errors.InvalidCompressor as e:
            continue
        else:
            log.info(f"found compressor {c.compression_algorithm}")
            break
    else:
        log.info(f"image does not appear to be compressed.")
        compressor = Compressor(raw_data)
    return compressor
