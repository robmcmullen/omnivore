import os
import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from .utils import to_numpy, to_numpy_list, uuid
from .container import guess_container
from .archiver import Archiver, find_container_items_in_archive
from .filesystem import Dirent

import logging
log = logging.getLogger(__name__)


class Collection:
    """Parent object for single file archive collection of multiple disk images

    Instances of this class are not `Segment`s, but instead hold a list of
    `Container`s, each of which will have its own media type and filesystem
    structure, independent of the other disk images.
    """
    ui_name = "Collection"

    def __init__(self, pathname, data):
        self.pathname = pathname
        self.filename = os.path.basename(pathname)
        self.name = ""
        self.containers = []
        self.archiver = None
        self.unarchive(data)

    @property
    def verbose_info(self):
        lines = []
        name = self.name or self.filename
        lines.append(f"{name}: {self}")
        for c in self.containers:
            lines.append(c.container_info("    "))
        return "\n".join(lines)

    @property
    def basename(self):
        return os.path.basename(self.pathname)

    #### dunder methods

    def __str__(self):
        desc = ""
        if len(self) > 1:
            desc = f"{len(self)} item "
        desc += f"{str(self.archiver)}"
        return desc

    def __len__(self):
        return np.alen(self.containers)

    #### compression

    def unarchive(self, byte_data):
        """Attempt to unpack `byte_data` using this archive unpacker.

        Calls `find_containers` to loop through each container found. The order
        listed here will be the order returned by the subclass; no sorting is
        done here.
        """
        self.archiver, item_data_list = find_container_items_in_archive(self.pathname, byte_data)
        for item_data in item_data_list:
            log.info(f"container size: {len(item_data)}")
            container = guess_container(item_data)
            container.guess_media_type()
            container.media.guess_filesystem()
            self.containers.append(container)
            container.name = f"D{len(self.containers)}"
            log.info(f"container: {container}")

    def iter_archive(self, byte_data):
        """Return a list of `Container` objects for each item in the archive.

        If the data is not recognized by this subclass, raise an
        InvalidContainer exception. This signals to the caller that a different
        container type should be tried.

        If the data is recognized by this subclass but the unpacking algorithm
        is not implemented, raise an UnsupportedContainer exception. This is
        different than the InvalidContainer exception because it indicates that
        the data was indeed recognized by this subclass (despite not being
        unpacked) and checking further containers is not necessary.
        """
        return [byte_data]

    def archive(self, fh):
        """Pack each container into the archive
        """
        return self.archive.pack_data(fh, self.containers)

    #### iterators

    def iter_dirents(self):
        for container in self.containers:
            for segment in container.media.segments:
                if isinstance(segment, Dirent):
                    yield segment
                yield from segment.yield_for_segment(Dirent)
