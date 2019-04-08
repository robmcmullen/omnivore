import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .segment import Segment
from .utils import to_numpy, to_numpy_list, uuid
from . import filesystem
from .file_type import guess_file_type
from .signature import guess_signature_by_size

import logging
log = logging.getLogger(__name__)


class MediaType(Segment):
    """Base class for what is typically the root segment in a Container,
    describing the type of media the data represents: floppy disk image,
    cassette image, cartridge, etc.
    """
    pretty_name = "Non-standard media"
    can_resize_default = False

    extra_serializable_attributes = []

    def __init__(self, container):
        self.filesystem = None
        self.header = self.calc_header(container)
        self.header_length = len(self.header) if self.header else 0
        size = len(container) - self.header_length
        Segment.__init__(self, container, self.header_length, name=self.pretty_name, length=size)
        if self.header is not None:
            self.check_header()
        self.check_media_size()
        self.check_magic()

    def __str__(self):
        desc = f"{self.pretty_name}, "
        if len(self.segments) == 1:
            desc += str(self.segments[0])
        else:
            desc += f"size={len(self)}"
        return desc

    #### initialization

    def calc_header(self, container):
        """Subclasses should override this method to verify the integrity of
        any header information, if any.

        If a header does exist, the subclass must return a `Segment` containing
        the header.

        Subclasses should raise the appropriate MediaError if the data is
        incompatible with this media type.
        """
        pass

    def check_header(self):
        """Subclasses should override this method to verify that header data is
        consistent with the media segment.

        Subclasses should raise the appropriate MediaError if the header and
        data are inconsistent.
        """
        pass

    def check_media_size(self):
        """Subclasses should override this method to verify that the payload
        portion of the media (i.e. everything after the header) can be stored
        in this media.

        Subclasses should raise the appropriate MediaError if the data is
        incompatible with this media type.
        """
        pass

    def check_magic(self):
        """Subclasses should override this method if there is some "magic"
        values that can identify (or rule out) this disk image class as a
        canditate.

        Subclasses should raise the appropriate MediaError if the data is
        incompatible with this media type.
        """
        pass

    def guess_filesystem(self):
        fs = filesystem.guess_filesystem(self)
        if fs:
            self.filesystem = fs
            self.segments = list(fs.iter_segments())
        else:
            log.info("Checking for file without filesystem")
            self.segments = [guess_file_type(self, self.container.name, 0, len(self))]


class DiskImage(MediaType):
    pretty_name = "Disk Image"
    sector_size = 128
    expected_size = 0
    starting_sector_label = 1

    def __init__(self, container):
        self.num_sectors = 0
        MediaType.__init__(self, container)

    # def __str__(self):
    #     return f"{self.pretty_name}, size={len(self)} ({self.num_sectors}x{self.sector_size}B)"

    #### verification

    def check_media_size(self):
        self.check_disk_size()
        self.num_sectors = self.calc_num_sectors()

    def check_disk_size(self):
        size = len(self)
        if size != self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} expects size {self.expected_size}; found {size}")

    def calc_num_sectors(self):
        size = len(self)
        if size % self.sector_size != 0:
            raise errors.InvalidMediaSize("{self.pretty_name} requires integer number of sectors")
        return size // self.sector_size

    #### sector operations

    def label(self, index, lower_case=True):
        sector, byte = divmod(index, self.sector_size)
        if lower_case:
            return "s%03d:%02x" % (sector + self.first_sector, byte)
        return "s%03d:%02X" % (sector + self.first_sector, byte)

    def is_sector_valid(self, sector):
        return (self.num_sectors < 0) or (sector >= self.starting_sector_label and sector < (self.num_sectors + self.starting_sector_label))

    def get_index_of_sector(self, sector):
        if not self.is_sector_valid(sector):
            raise errors.InvalidSectorNumber("Sector %d out of range" % sector)
        pos = (sector - self.starting_sector_label) * self.sector_size
        return pos, self.sector_size

    def get_contiguous_sectors_offsets(self, start, count=1):
        index, _ = self.get_index_of_sector(start)
        last, size = self.get_index_of_sector(start + count - 1)
        return index, last + size - index

    def get_contiguous_sectors(self, start, count=1):
        start, size = self.get_contiguous_sectors_offsets(start, count)
        return Segment(self, start, length=size)

    def get_sector_list_offsets(self, sector_numbers):
        offsets = np.empty(len(sector_numbers) * self.sector_size, dtype=np.uint32)
        i = 0
        for num in sector_numbers:
            index, size = self.get_index_of_sector(num)
            offsets[i:i+size] = np.arange(index, index + size)
            i += size
        return offsets

    def get_sector_list(self, sector_numbers):
        offsets = self.get_sector_list_offsets(sector_numbers)
        return Segment(self, offsets)

    def iter_sectors(self):
        i = self.starting_sector_label
        while self.is_sector_valid(i):
            pos, size = self.get_index_of_sector(i)
            yield i, pos, size
            i += 1


class CartImage(MediaType):
    pretty_name = "Cart Image"
    expected_size = 0

    # def __str__(self):
    #     return f"{len(self) // 1024}K {self.pretty_name}"

    def check_media_size(self):
        size = len(self)
        k, rem = divmod(size, 1024)
        if rem > 0:
            raise errors.InvalidMediaSize("Cart not multiple of 1K")
        if self.expected_size == 0:
            raise errors.InvalidMediaSize(f"Possible cart image, but unable to identify specifically")
        if size != self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} expects size {self.expected_size}; found {size}")


ignore_base_class_media_types = set([DiskImage, CartImage])

_media_types = None

def _find_media_types():
    media_types = []
    for entry_point in pkg_resources.iter_entry_points('atrip.media_types'):
        mod = entry_point.load()
        log.debug(f"find_media_type: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and MediaType in obj.__mro__[1:] and obj not in ignore_base_class_media_types:
                log.debug(f"find_media_types:   found media_type class {name}")
                media_types.append(obj)
    return media_types

def find_media_types():
    global _media_types

    if _media_types is None:
        _media_types = _find_media_types()
    return _media_types

def guess_media_type(container, verbose=False):
    signature = guess_signature_by_size(container, verbose)
    if signature:
        log.info(f"found signature {signature}")
    for m in find_media_types():
        if verbose:
            log.info(f"trying media_type {m}")
        try:
            found = m(container)
        except errors.MediaError as e:
            log.debug(f"found error: {e}")
            continue
        else:
            if verbose:
                log.info(f"found media_type {m}")
            return found
    log.info(f"No recognized media type.")
    return MediaType(container)
