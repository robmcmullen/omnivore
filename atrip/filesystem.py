import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .segment import Segment
from .utils import to_numpy, to_numpy_list, uuid
from .file_type import guess_file_type

import logging
log = logging.getLogger(__name__)

try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class Filesystem:
    """Base class for a "filesystem", which takes a source segment and
    subdivides it into a set of segments where each represents a file. Some
    auxiliary segments include a `VTOC` and a list of `Dirent`s that point to
    files.

    It is used to fill a `Media` instance with segments.
    """
    ui_name = "Filesystem"

    extra_serializable_attributes = []

    def __init__(self, media):
        self.check_media(media)
        self.media = media
        self.boot = self.calc_boot_segment()
        self.vtoc = self.calc_vtoc_segment()
        self.directory = self.calc_directory_segment()
        media.segments = list(self.filesystem_metadata_segments())

    #### initialization

    def check_media(self, media):
        """Subclasses should override this method to verify the media type is
        supported by the filesystem.

        Subclasses should raise IncompatibleMediaError if the filesystem is not
        possible on this media, for instance attempting to use a disk
        filesystem on a cassette media image.
        """
        pass

    def calc_boot_segment(self):
        """Subclasses should override this method to create a boot segment if
        the filesystem supports one and it is present.

        If it is present, return a single `Segment` instance comprising the
        entire set of data, and use sub-segments if more detail is present.

        If this feature is not present, return None.

        Subclasses should raise the appropriate FilesystemError if the data is
        incompatible with this filesystem.
        """
        pass

    def calc_vtoc_segment(self):
        """Subclasses should override this method to create a VTOC segment if
        the filesystem supports one and it is present.

        If it is present, return a single `Segment` instance comprising the
        entire set of data, and use sub-segments if more detail is present.

        If this feature is not present, return None.

        Subclasses should raise the appropriate FilesystemError if the data is
        incompatible with this filesystem.
        """
        pass

    def calc_directory_segment(self):
        """Subclasses should override this method to create a directory segment
        if the filesystem supports one and it is present.

        If it is present, return a single `Segment` instance comprising the
        entire set of data, and use sub-segments if more detail is present.

        If this feature is not present, return None.

        Subclasses should raise the appropriate FilesystemError if the data is
        incompatible with this filesystem.
        """
        pass

    ####

    @property
    def max_file_size(self):
        return len(self.media)

    #### iterators

    def filesystem_metadata_segments(self):
        if self.boot is not None:
            yield self.boot
        if self.vtoc is not None:
            yield self.vtoc
        if self.directory is not None:
            yield self.directory

    def iter_dirents(self):
        for segment in self.media.segments:
            if isinstance(segment, Dirent):
                yield segment
            yield from segment.iter_segments(Dirent)

    #### utilities

    def find_interesting_segment(self):
        """If the filesystem has some interesting segment that might be better
        to display than the first segment in the container, identify that here
        and an editor can use this info to display that segment in the initial
        view.
        """
        return None


class NoFilesystem(Filesystem):
    ui_name = "No Filesystem"

    def filesystem_metadata_segments(self):
        media = self.media
        segment = guess_file_type(media, media.container.basename, 0, len(media))
        yield segment


class Dirent(Segment):
    """Abstract base class for a directory entry

    """
    ui_name = "Dirent"
    extra_serializable_attributes = ['file_num', 'in_use', 'is_sane']

    def __init__(self, directory, file_num, start, length, parent=None):
        self.directory = directory
        self.file_num = file_num
        self.in_use = True
        self.is_sane = True
        if parent is None:
            parent = directory
        Segment.__init__(self, parent, start, name=f"{self.ui_name} {file_num}", length=length)
        self.init_dirent()

    def init_dirent(self):
        self.parse_raw_dirent()
        if self.sanity_check():
            self.is_sane = True
        else:
            self.is_sane = False
            self.in_use = False
        if self.in_use:
            try:
                self.get_file()
            except errors.FileError as e:
                self.in_use = False
                self.is_sane = False
                self.error = e

    def __eq__(self, other):
        raise NotImplementedError

    def __str__(self):
        return "File #%-2d %s %s" % (self.file_num, f"({self.status})" if self.status else "", self.catalog_entry)

    @property
    def verbose_info(self):
        return ""

    @property
    def status(self):
        return ""

    @property
    def catalog_entry(self):
        return self.filename

    @property
    def filesystem(self):
        return self.directory.filesystem

    @property
    def media(self):
        return self.directory.filesystem.media

    def sanity_check(self):
        return True

    def extra_metadata(self, image):
        return self.verbose_info

    def mark_deleted(self):
        self.deleted = True
        self.in_use = False

    def parse_raw_dirent(self):
        raise NotImplementedError

    def encode_dirent(self):
        raise NotImplementedError

    def get_file(self):
        raise NotImplementedError


class Directory(Segment):
    ui_name = "Directory"

    def __init__(self, filesystem):
        self.filesystem = filesystem
        offset, length = self.find_segment_location()
        Segment.__init__(self, filesystem.media, offset, name=self.ui_name, length=length)

        # Each segment is a dirent
        self.segments = self.calc_dirents()

    @property
    def media(self):
        return self.filesystem.media

    def find_segment_location(self):
        raise NotImplementedError("Subclasses must define this to declare where the directory segment is located in the media image")

    def calc_dirents(self):
        raise NotImplementedError("Subclasses must define this to generate a list of Dirent segments")

    def set(self, index, dirent):
        self.segments[index] = dirent
        if _xd: log.debug("set dirent #%d: %s" % (index, dirent))

    def get_free_dirent(self):
        used = set()
        d = list(self.segments.items())
        if d:
            d.sort()
            for i, dirent in d:
                if not dirent.in_use:
                    return i
                used.add(i)
            if self.num_dirents > 0 and (len(used) >= self.num_dirents):
                raise errors.NoSpaceInDirectory()
            i += 1
        else:
            i = 0
        used.add(i)
        return i

    def add_dirent(self, filename, filetype):
        index = self.get_free_dirent()
        dirent = self.dirent_class(None)
        dirent.set_values(filename, filetype, index)
        self.set(index, dirent)
        return dirent

    def find_dirent(self, filename):
        if hasattr(filename, "filename"):
            # we've been passed a dirent instead of a filename
            for dirent in list(self.segments.values()):
                if dirent == filename:
                    return dirent
        else:
            for dirent in list(self.segments.values()):
                if filename == dirent.filename:
                    return dirent
        raise errors.FileNotFound("%s not found on disk" % filename)

    def save_dirent(self, image, dirent, vtoc, sector_list):
        vtoc.assign_sector_numbers(dirent, sector_list)
        dirent.add_metadata_sectors(vtoc, sector_list, image.header)
        dirent.update_sector_info(sector_list)
        self.calc_sectors(image)

    def remove_dirent(self, image, dirent, vtoc, sector_list):
        vtoc.free_sector_list(sector_list)
        dirent.mark_deleted()
        self.calc_sectors(image)

    @property
    def dirent_class(self):
        raise NotImplementedError

    def calc_sectors(self, image):
        self.sectors = []
        self.current_sector = self.get_dirent_sector()
        self.encode_index = 0

        d = list(self.segments.items())
        d.sort()
        # there may be gaps, so fill in missing entries with blanks
        current = 0
        for index, dirent in d:
            for missing in range(current, index):
                if _xd: log.debug("Encoding empty dirent at %d" % missing)
                data = self.encode_empty()
                self.store_encoded(data)
            if _xd: log.debug("Encoding dirent: %s" % dirent)
            data = self.encode_dirent(dirent)
            self.store_encoded(data)
            current = index + 1
        self.finish_encoding(image)

    def get_dirent_sector(self):
        return self.sector_class(self.sector_size)

    def encode_empty(self):
        raise NotImplementedError

    def encode_dirent(self, dirent):
        raise NotImplementedError

    def store_encoded(self, data):
        while True:
            if _xd: log.debug("store_encoded: %d bytes in %s" % (len(data), self.current_sector))
            data = self.current_sector.add_data(data)
            if len(data) > 0:
                self.sectors.append(self.current_sector)
                self.current_sector = self.get_dirent_sector()
            else:
                break

    def finish_encoding(self, image):
        if not self.current_sector.is_empty:
            self.sectors.append(self.current_sector)
        self.set_sector_numbers(image)

    def set_sector_numbers(self, image):
        raise NotImplementedError


class VTOC(Segment):
    ui_name = "VTOC"

    extra_serializable_attributes = ['addressable_sectors', 'sector_map']

    def __init__(self, filesystem):
        self.filesystem = filesystem
        offset, length = self.find_segment_location()
        Segment.__init__(self, filesystem.media, offset, name=self.ui_name, length=length)
        self.addressable_sectors = self.calc_sector_map_size()
        self.create_sector_map()
        self.unpack_vtoc()

    @property
    def media(self):
        return self.filesystem.media

    def find_segment_location(self):
        """Calculate the location on the media for the VTOC. Return either
        sector number and count, or offset list
        """
        raise NotImplementedError("Subclasses must define this to declare where the directory segment is located in the media image")

    # def __str__(self):
    #     return "%s\n (%d free)" % ("\n".join(["track %02d: %s" % (i, line) for i, line in enumerate(str(self.sector_map[self.header.starting_sector_label:(self.header.tracks_per_disk*self.header.sectors_per_track) + self.header.starting_sector_label].reshape([self.header.tracks_per_disk,self.header.sectors_per_track])).splitlines())]), self.num_free_sectors)

    def calc_sector_map_size(self):
        return self.media.num_sectors

    def create_sector_map(self):
        # sector map: 1 is free, 0 is allocated
        self.sector_map = np.zeros([self.addressable_sectors], dtype=np.uint8)

    def unpack_vtoc(self):
        """Using the bit-encoded data, unpack it into the sector_map array
        """
        raise NotImplementedError

    def pack_vtoc(self):
        """Pack the sector_map array into the segment
        """
        raise NotImplementedError

    @property
    def num_free_sectors(self):
        free = np.where(self.sector_map == 1)[0]
        return len(free)

    def iter_free_sectors(self):
        for i, pos, size in self.filesystem.media.iter_sectors():
            if self.sector_map[i] == 1:
                yield i, pos, size

    def assign_sector_numbers(self, dirent, sector_list):
        """ Map out the sectors and link the sectors together

        raises NotEnoughSpaceOnDisk if the whole file won't fit. It will not
        allow partial writes.
        """
        num = len(sector_list)
        order = self.reserve_space(num)
        if len(order) != num:
            raise errors.NotEnoughSpaceOnDisk(f"Need {num} sectors, VTOC has only {len(order)} available")
        file_length = 0
        last_sector = None
        for sector, sector_num in zip(sector_list.sectors, order):
            sector.sector_num = sector_num
            sector.file_num = dirent.file_num
            file_length += sector.used
            if last_sector is not None:
                last_sector.next_sector_num = sector_num
            last_sector = sector
        if last_sector is not None:
            last_sector.next_sector_num = 0
        sector_list.file_length = file_length

    def reserve_space(self, num):
        order = []
        for i in range(num):
            order.append(self.get_next_free_sector())
        if _xd: log.debug("Sectors reserved: %s" % order)
        self.calc_bitmap()
        return order

    def get_next_free_sector(self):
        free = np.nonzero(self.sector_map)[0]
        if len(free) > 0:
            num = free[0]
            if _xd: log.debug("Found sector %d free" % num)
            self.sector_map[num] = 0
            return num
        raise errors.NotEnoughSpaceOnDisk("No space left in VTOC")

    def calc_bitmap(self):
        raise NotImplementedError

    def free_sector_list(self, sector_list):
        for sector in sector_list:
            self.sector_map[sector.sector_num] = 1
        self.calc_bitmap()


_filesystems = None

def _find_filesystems():
    filesystems = []
    for entry_point in pkg_resources.iter_entry_points('atrip.filesystems'):
        mod = entry_point.load()
        log.debug(f"find_filesystems: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and Filesystem in obj.__mro__[1:]:
                log.debug(f"find_filesystems:   found media_type class {name}")
                filesystems.append(obj)
    return filesystems

def find_filesystems():
    global _filesystems

    if _filesystems is None:
        _filesystems = _find_filesystems()
    return _filesystems

def guess_filesystem(segment):
    for f in find_filesystems():
        log.debug(f"trying filesystem {f.ui_name}")
        try:
            found = f(segment)
        except errors.FilesystemError as e:
            log.debug(f"found error: {e}")
            continue
        except errors.MediaError as e:
            log.debug(f"found media error: {e}")
            continue
        else:
            log.info(f"found filesystem {f.ui_name}")
            return found
    log.info(f"No recognized filesystem.")
    return NoFilesystem(segment)
