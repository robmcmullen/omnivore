import os
import inspect
import pkg_resources

from . import errors

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
    compression_algorithm = None

    def __init__(self, byte_data=None):
        if byte_data is not None:
            self.unpacked = self.calc_unpacked_data(byte_data)

    def __str__(self):
        return self.compression_algorithm

    @property
    def is_compressed(self):
        return self.compression_algorithm != Uncompressed.compression_algorithm

    #### decompression

    def calc_unpacked_data(self, byte_data):
        """Attempt to unpack `byte_data` using this unpacking algorithm.

        `byte_data` must be a byte array or something that can pose for a byte
        array.

        If the data is not recognized by this subclass, raise an
        `InvalidAlgorithm` exception. The caller must recognize this and move
        on to trying the next compressor in the list.

        If the data is recognized by this subclass but the unpacking algorithm
        is not implemented, raise an `UnsupportedAlgorithm` exception. This
        is different than the `InvalidAlgorithm` exception because it
        indicates that the data was indeed recognized by this subclass (despite
        not being unpacked) and checking further compressors is not necessary.
        """
        raise errors.InvalidAlgorithm(f"Uncompressing '{self.compression_algorithm}' not implemented")

    #### compression

    def calc_packed_data(self, byte_data, media=None):
        """Pack this data into a compressed data array using this packing
        algorithm.

        Subclasses should raise the `UnsupportedAlgorithm` exception if
        compression is not implemented.

        `media` is supplied in case the compression format needs the disk
        geometry, e.g. in DCM compression.
        """
        raise errors.InvalidAlgorithm(f"Compression for '{self.compression_algorithm}' not implemented.")


class Uncompressed(Compressor):
    compression_algorithm = "none"

    def calc_unpacked_data(self, byte_data):
        return byte_data

    def calc_packed_data(self, byte_data, media):
        return byte_data


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

def find_compressor_by_name(name):
    items = find_compressors()
    for c in items:
        if c.compression_algorithm == name:
            return c()
    raise KeyError(f"Unknown compressor {name}")

def guess_compressor(raw_data):
    compressor = None
    for c in find_compressors():
        log.debug(f"trying compressor {c.compression_algorithm}")
        try:
            compressor = c(raw_data)
        except (errors.InvalidAlgorithm, IOError, EOFError) as e:
            continue
        else:
            log.info(f"found compressor {c.compression_algorithm}")
            break
    else:
        log.debug(f"image does not appear to be compressed.")
        compressor = Uncompressed(raw_data)
    return compressor

def guess_compressor_list(data):
    compressors = []
    while True:  # loop until reach an uncompressed state
        c = guess_compressor(data)
        data = c.unpacked
        if not c.is_compressed:
            if not compressors:
                # save the null compressor only if it's the only one
                log.info(f"image does not appear to be compressed.")
                compressors.append(c.__class__)
            break
        compressors.append(c.__class__)
    return data, compressors

def compress_in_reverse_order(byte_data, decompression_order, media=None, skip_missing_compressors=False):
    order = reversed(decompression_order)
    log.debug(f"compression_order: {order}")
    for compressor_cls in order:
        compressor = compressor_cls()
        try:
            byte_data = compressor.calc_packed_data(byte_data, media)
        except errors.InvalidAlgorithm:
            if skip_missing_compressors:
                continue
            else:
                log.error(f"Compression algorithm {compressor} not yet implemented")
                raise
    return byte_data
