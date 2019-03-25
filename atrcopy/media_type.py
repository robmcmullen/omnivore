import hashlib
import inspect
import pkg_resources

import numpy as np

from . import errors
from . import style_bits
from .segment import Segment
from .utils import to_numpy, to_numpy_list, uuid

import logging
log = logging.getLogger(__name__)


class MediaType(Segment):
    """Base class for what is typically the root segment in a Container,
    describing the type of media the data represents: floppy disk image,
    cassette image, cartridge, etc.
    """
    pretty_name = "Raw Data"
    can_resize_default = False

    extra_serializable_attributes = []

    def __init__(self, container):
        self.header = self.calc_header(container)
        self.header_length = len(self.header) if self.header else 0
        size = len(container) - self.header_length
        Segment.__init__(self, container, self.header_length, name=self.pretty_name, length=size)
        if self.header is not None:
            self.check_header()
        self.check_media_size()

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


class DiskImage(MediaType):
    pretty_name = "Disk Image"
    sector_size = 128
    expected_size = 0
    starting_sector_label = 1

    def __init__(self, container):
        self.num_sectors = 0
        MediaType.__init__(self, container)

    def __str__(self):
        return f"{self.pretty_name}, size={len(self)} ({self.num_sectors}x{self.sector_size}B)"

    @property
    def verbose_info(self):
        name = self.verbose_name or self.name
        if self.num_sectors > 1:
            s = "%s (sectors %d-%d)" % (name, self.first_sector, self.first_sector + self.num_sectors - 1)
        else:
            s = "%s (sector %d)" % (name, self.first_sector)
        s += " $%x bytes" % (len(self), )
        if self.error:
            s += "  error='%s'" % self.error
        return s

    #### verification

    def check_media_size(self):
        size = len(self)
        if size != self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} expects size {self.expected_size}; found {size}")
        self.num_sectors = self.calc_num_sectors()

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

    def sector_is_valid(self, sector):
        return (self.num_sectors < 0) or (sector >= self.starting_sector_label and sector < (self.num_sectors + self.starting_sector_label))

    def get_index_of_sector(self, sector):
        if not self.sector_is_valid(sector):
            raise errors.ByteNotInFile166("Sector %d out of range" % sector)
        pos = (sector - self.starting_sector_label) * self.sector_size
        return pos + self.header_length, self.sector_size


class CartImage(MediaType):
    pretty_name = "Cart Image"
    expected_size = 0

    def __str__(self):
        return f"{len(self) // 1024}K {self.pretty_name}"

    def check_media_size(self):
        size = len(self)
        k, rem = divmod(size, 1024)
        if rem > 0:
            raise errors.InvalidMediaSize("Cart not multiple of 1K")
        if size != self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} expects size {self.expected_size}; found {size}")


ignore_base_class_media_types = set([DiskImage, CartImage])

def find_media_types():
    media_types = []
    for entry_point in pkg_resources.iter_entry_points('atrcopy.media_types'):
        mod = entry_point.load()
        log.debug(f"find_media_type: Found module {entry_point.name}={mod.__name__}")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and MediaType in obj.__mro__[1:] and obj not in ignore_base_class_media_types:
                log.debug(f"find_media_types:   found media_type class {name}")
                media_types.append(obj)
    return media_types


def guess_media_type(container, verbose=False):
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
