import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .utils import to_numpy, to_numpy_list, uuid

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class Container:
    """Disk image data storage and unpacker for disk image compression.

    Segments point to this container and refer to the container's data rather
    than store copies.

    Disk images may be stored as raw data or can be compressed by any number of
    techniques. Subclasses of Container implement the `unpack_bytes`
    method which examines the byte_data argument for the supported compression
    type, and if valid returns the unpacked bytes to be used in the disk image
    parsing.
    """


def find_containers():
    containers = []
    for entry_point in pkg_resources.iter_entry_points('atrcopy.containers'):
        mod = entry_point.load()
        log.debug(f"find_container: Found module {entry_point.name}={mod.__name__}")
        containers.append(mod)
    return containers


def guess_container(raw_data):
    uncompressed = raw_data
    for c in find_containers():
        log.info(f"trying container {c}")
        try:
            uncompressed = c.unpack_bytes(raw_data)
        except errors.InvalidContainer as e:
            continue
        else:
            log.info(f"found container {c}")
            break
    else:
        c = None
        log.info(f"image does not appear to be compressed.")
    return c, uncompressed
