import os
import io
import hashlib
import weakref

import numpy as np

from . import errors
from .utils import to_numpy, to_numpy_list, uuid
from .container import guess_container, Container, ContainerHeader
from .compressor import guess_compressor_list, compress_in_reverse_order, Uncompressed
from .archiver import Archiver, find_container_items_in_archive, PlainFileArchiver
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

    def __init__(self, pathname, data=None, session=None, container=None, guess=True):
        self.pathname = pathname
        self.name = ""
        self.containers = []
        self.decompression_order = [Uncompressed]
        self._uuid_map = None
        self.archiver = None
        if container is None:
            if data is None:
                data = open(pathname, 'rb').read()
                log.debug(f"Collection.__init__: {pathname}: read {len(data)} bytes")
            self.unarchive(data, session)
        else:
            self.archiver = PlainFileArchiver()
            self.add_container(container, pathname, guess=guess)

    @property
    def verbose_info(self):
        lines = []
        name = self.name or self.pathname
        lines.append(f"{name}: {self}")
        for c in self.containers:
            lines.append(c.container_info("    "))
        return "\n".join(lines)

    @property
    def basename(self):
        return os.path.basename(self.pathname)

    @property
    def mime_type(self):
        return "application/octet-stream"

    @property
    def uuid_map(self):
        if self._uuid_map is None:
            self._uuid_map = {}
            for segment in self.iter_segments():
                self._uuid_map[segment.uuid] = weakref.ref(segment)
            log.debug(f"created uuid map: {self._uuid_map}")
        return self._uuid_map

    #### dunder methods

    def __str__(self):
        desc = ""
        if len(self) > 1:
            desc = f"{len(self)} item "
        desc += f"{str(self.archiver)}"
        return desc

    def __len__(self):
        return np.alen(self.containers)

    def __getitem__(self, index):
        """Returns segment given the uuid, raising KeyError if not found
        """
        ref = self.uuid_map[index]
        segment = ref()
        return segment

    #### decompression

    def add_container(self, container, pathname, guess=True):
        container.pathname = pathname
        if guess:
            container.guess_media_type()
            container.guess_filesystem()
        self.containers.append(container)
        container.name = f"D{len(self.containers)}"
        log.info(f"container: {container}")

    def unarchive(self, byte_data, session=None):
        """Attempt to unpack `byte_data` using this archive unpacker.

        Calls `find_containers` to loop through each container found. The order
        listed here will be the order returned by the subclass; no sorting is
        done here.
        """
        decompressed_archive_byte_data, decompression_list = guess_compressor_list(byte_data)
        self.archiver, item_data_list = find_container_items_in_archive(self.pathname, decompressed_archive_byte_data)
        if session is not None:
            self.restore_session(session, item_data_list)
        elif not self.archiver.supports_multiple_containers:
            item_pathname, item_data = item_data_list[0]
            container = Container(item_data, decompression_list)
            self.add_container(container, item_pathname)
        else:
            self.decompression_order = decompression_list
            for item_pathname, item_data in item_data_list:
                log.info(f"container size: {len(item_data)}")
                container = guess_container(item_data)
                self.add_container(container, item_pathname)
        self._uuid_map = None

    def iter_archive(self, basename, byte_data):
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
        return [basename, byte_data]

    #### compression and save

    def save(self, pathname=None, skip_missing_compressors=False):
        """Save the collection.

        If pathname is None, will attempt to overwrite the file that used to
        load the collection.

        Can raise InvalidAlgorithm if one of the compressors is read-only
        (i.e. can only decompress data). However, if `skip_missing_compressors`
        is True, no error will be raised and compression will take place
        ignoring any compressors that can't compress data.
        """
        if pathname is None:
            pathname = self.pathname
        compressed_bytes = self.calc_compressed_data(skip_missing_compressors)
        with open(pathname, 'wb') as fh:
            fh.write(compressed_bytes)

    def calc_compressed_data(self, skip_missing_compressors=False):
        fh = io.BytesIO()
        self.save_in_archive(fh, skip_missing_compressors)
        archived_bytes = fh.getvalue()
        compressed_bytes = compress_in_reverse_order(archived_bytes, self.decompression_order)
        return compressed_bytes

    def save_in_archive(self, fh, skip_missing_compressors=False):
        """Pack each container into the archive
        """
        return self.archiver.pack_data(fh, self.containers, skip_missing_compressors)

    #### iterators

    def iter_segments(self):
        for container in self.containers:
            yield from container.iter_segments()

    def iter_menu(self):
        for container in self.containers:
            yield (container, 0)
            yield from container.iter_menu(1)

    def iter_dirents(self):
        for container in self.containers:
            yield from container.iter_dirents()

    #### search utilities

    def find_interesting_segment_to_edit(self):
        """Find the the first segment that might be "interesting" that an
        editor can use as an initial segment display.

        Largely depends on the filesystem to locate something interesting.

        Returns: None if nothing is super interesting
        """
        segment = None
        for container in self.containers:
            if container.filesystem is not None:
                segment = container.filesystem.find_interesting_segment()
                if segment is not None:
                    break
        return segment

    def find_boot_media(self):
        """Find the first bootable media in the collection.

        Should usually be in the first container, but will continue looking
        through containers if not in the first.
        """
        for container in self.containers:
            if container.media is not None:
                return container.media
        log.warning(f"No bootable media found in {self}, attempting to find an interesting segment")
        for s in self.iter_segments():
            if isinstance(s, ContainerHeader):
                continue
            return s
        else:
            try:
                return self.containers[0]
            except IndexError:
                raise errors.MediaError("find_boot_media: no containers, so no booting!")

    def find_dirent(self, filename, match_case=False):
        try:
            disk_input, pathname = filename.split(":", 1)
        except ValueError:
            disk_input = "D1"
            pathname = filename
        disk = disk_input.upper()
        try:
            if disk.startswith("D"):
                disk = disk[1:]
            disk_num = int(disk)
        except ValueError:
            raise errors.FileNotFound(f"Invalid disk specifier {disk_input}")
        try:
            container = self.containers[disk_num - 1]  # disk numbers 1 based
        except IndexError:
            raise errors.FileNotFound(f"Disk {disk_input} doesn't exist")
        return container.find_dirent(pathname, match_case)

    def find_uuid(self, uuid):
        try:
            segment = self[uuid]
        except KeyError:
            raise errors.InvalidSegment(f"No segment in any disk with uuid={uuid}")
        return segment

    #### session

    def serialize_session(self, e):
        """Save session information to a dict so that it can be serialized.

        Note that only the structure of the containers is saved, not the byte
        data. Styling and disassembler info is saved, however.
        """
        e["pathname"] = self.pathname
        e["name"] = self.name
        e["archiver"] = self.archiver
        e["containers"] = self.containers

    def restore_session(self, e, item_data_list=None):
        # log.debug("restoring sesssion data: %s" % str(e))
        self.pathname = e["pathname"]
        self.name = e["name"]
        self.archiver = e["archiver"]

        if item_data_list is None:
            item_data_list = [(c.pathname, c._data) for c in self.containers]

        # unless restoring a session over top of existing containers, the
        # containers will have been initialized with zeros from the jsonpickle
        # restore. The arrays will be the correct size, so all we have to do is
        # copy the actual data into the containers.
        self.containers = e["containers"]
        for c, (item_pathname, item_data) in zip(self.containers, item_data_list):
            c._data[:] = np.frombuffer(item_data, dtype=np.uint8)
            c.pathname = item_pathname
