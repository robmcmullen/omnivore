import os
import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from .utils import to_numpy, to_numpy_list, uuid

import logging
log = logging.getLogger(__name__)


class Archiver:
    archive_type = ""

    supports_multiple_containers = True

    def __str__(self):
        return self.archive_type + " archive"

    def iter_archive(self, basename, byte_data):
        yield basename, byte_data

    def pack_data(self, fh, containers, skip_missing_compressors=False):
        raise NotImplementedError


class PlainFileArchiver:
    archive_type = "plain file"

    supports_multiple_containers = False

    def __str__(self):
        return self.archive_type

    def iter_archive(self, basename, byte_data):
        yield basename, byte_data

    def pack_data(self, fh, containers, skip_missing_compressors=False):
        if len(containers) > 1:
            raise errors.InvalidArchiver(f"{str(self)} doesn't support multiple containers")
        fh.write(containers[0].calc_packed_bytes(skip_missing_compressors))


_archivers = None

def _find_archivers():
    archivers = []
    for entry_point in pkg_resources.iter_entry_points('atrip.archivers'):
        mod = entry_point.load()
        log.debug(f"find_archiver: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and Archiver in obj.__mro__[1:]:
                log.debug(f"find_archivers:   found archiver class {name}")
                archivers.append(obj)

    return archivers

def find_archivers():
    global _archivers

    if _archivers is None:
        _archivers = _find_archivers()
    return _archivers

def find_container_items_in_archive(pathname, raw_data):
    basename = os.path.basename(pathname)
    archiver = None
    for c in find_archivers():
        items = []
        log.debug(f"trying archiver {c.archive_type}")
        try:
            archiver = c()
            items = list(archiver.iter_archive(basename, raw_data))
        except errors.InvalidArchiver as e:
            continue
        else:
            log.info(f"found archiver {c.archive_type}")
            return archiver, items
    else:
        log.info(f"image does not appear to be archived.")
    return PlainFileArchiver(), [(basename, raw_data),]
