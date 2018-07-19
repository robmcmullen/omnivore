import os

import numpy as np

from . import errors
from .segments import SegmentData, EmptySegment, ObjSegment
from .diskimages import DiskImageBase
from .utils import to_numpy

import logging
log = logging.getLogger(__name__)


class LocalFilesystemImage(DiskImageBase):
    def __init__(self, path):
        self.path = path

    def __str__(self, path="."):
        return f"Local filesystem output to: {self.path}"

    def save(self, filename=""):
        # This is to save the disk image containing the files on the disk image
        # to the local disk, which doesn't make sense when the disk image is
        # the filesystem.
        pass

    def find_dirent(self, name):
        path = os.path.join(self.path, name)
        if os.path.exists(path):
            return True
        raise errors.FileNotFound("%s not found on disk" % str(name))

    def write_file(self, name, filetype, data):
        path = os.path.join(self.path, name)
        with open(path, "wb") as fh:
            fh.write(data)

    def delete_file(self, name):
        pass


class LocalFilesystem():
    def __init__(self, path="."):
        self.image = LocalFilesystemImage(path)
