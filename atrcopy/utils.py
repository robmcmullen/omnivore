import types
import uuid as stdlib_uuid

import numpy as np

from . import errors

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


def uuid():
    u = stdlib_uuid.uuid4()

    # Force it to use unicode(py2) or str(py3) so it isn't serialized as
    # future.types.newstr.newstr on py2
    try:
        u = unicode(u)
    except:
        u = str(u)
    return u


def to_numpy(value):
    if type(value) is np.ndarray:
        return value
    elif type(value) is bytes:
        return np.fromstring(value, dtype=np.uint8)
    elif type(value) is list:
    	return np.asarray(value, dtype=np.uint8)
    raise TypeError("Can't convert to numpy data")


def to_numpy_list(value):
    if type(value) is np.ndarray:
        return value
    return np.asarray(value, dtype=np.uint32)


def text_to_int(text, default_base="hex"):
    """ Convert text to int, raising exeception on invalid input
    """
    if text.startswith("0x"):
        value = int(text[2:], 16)
    elif text.startswith("$"):
        value = int(text[1:], 16)
    elif text.startswith("#"):
        value = int(text[1:], 10)
    elif text.startswith("%"):
        value = int(text[1:], 2)
    else:
        if default_base == "dec":
            value = int(text)
        else:
            value = int(text, 16)
    return value


class WriteableSector:
    def __init__(self, sector_size, data=None, num=-1):
        self._sector_num = num
        self._next_sector = 0
        self.sector_size = sector_size
        self.file_num = 0
        self.data = np.zeros([sector_size], dtype=np.uint8)
        self.used = 0
        self.ptr = self.used
        if data is not None:
            self.add_data(data)

    def __str__(self):
        return "sector=%d next=%d size=%d used=%d" % (self._sector_num, self._next_sector, self.sector_size, self.used)

    @property
    def sector_num(self):
        return self._sector_num

    @sector_num.setter
    def sector_num(self, value):
        self._sector_num = value

    @property
    def next_sector_num(self):
        return self._next_sector_num

    @sector_num.setter
    def next_sector_num(self, value):
        self._next_sector_num = value

    @property
    def space_remaining(self):
        return self.sector_size - self.ptr

    @property
    def is_empty(self):
        return self.ptr == 0

    def add_data(self, data):
        count = len(data)
        if self.ptr + count > self.sector_size:
            count = self.space_remaining
        self.data[self.ptr:self.ptr + count] = data[0:count]
        self.ptr += count
        self.used += count
        return data[count:]


class BaseSectorList:
    def __init__(self, header):
        self.header = header
        self.sector_size = header.sector_size
        self.sectors = []

    def __len__(self):
        return len(self.sectors)

    def __str__(self):
        return "\n".join(" %d: %s" % (i, str(s)) for i, s in enumerate(self))

    def __getitem__(self, index):
        if index < 0 or index >= len(self):
            raise IndexError
        return self.sectors[index]

    @property
    def num_sectors(self):
        return len(self.sectors)

    @property
    def first_sector(self):
        if self.sectors:
            return self.sectors[0].sector_num
        return -1

    @property
    def bytes_used(self):
        size = 0
        for s in self:
            size += s.used
        return size

    def append(self, sector):
        self.sectors.append(sector)

    def extend(self, sectors):
        self.sectors.extend(sectors)


class Dirent:
    """Abstract base class for a directory entry

    """

    def __init__(self, file_num=0):
        self.file_num = file_num

    def __eq__(self, other):
        raise errors.NotImplementedError

    def extra_metadata(self, image):
        raise errors.NotImplementedError

    def mark_deleted(self):
        raise errors.NotImplementedError

    def parse_raw_dirent(self, image, bytes):
        raise errors.NotImplementedError

    def encode_dirent(self):
        raise errors.NotImplementedError

    def get_sectors_in_vtoc(self, image):
        raise errors.NotImplementedError

    def start_read(self, image):
        raise errors.NotImplementedError

    def read_sector(self, image):
        raise errors.NotImplementedError


class Directory(BaseSectorList):
    def __init__(self, header, num_dirents=-1, sector_class=WriteableSector):
        BaseSectorList.__init__(self, header)
        self.sector_class = sector_class
        self.num_dirents = num_dirents
        # number of dirents may be unlimited, so use a dict instead of a list
        self.dirents = {}

    def set(self, index, dirent):
        self.dirents[index] = dirent
        if _xd: log.debug("set dirent #%d: %s" % (index, dirent))

    def get_free_dirent(self):
        used = set()
        d = list(self.dirents.items())
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
            for dirent in list(self.dirents.values()):
                if dirent == filename:
                    return dirent
        else:
            for dirent in list(self.dirents.values()):
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
        raise errors.NotImplementedError

    def calc_sectors(self, image):
        self.sectors = []
        self.current_sector = self.get_dirent_sector()
        self.encode_index = 0

        d = list(self.dirents.items())
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
        raise errors.NotImplementedError

    def encode_dirent(self, dirent):
        raise errors.NotImplementedError

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
        raise errors.NotImplementedError


class VTOC(BaseSectorList):
    def __init__(self, header, segments=None):
        BaseSectorList.__init__(self, header)

        # sector map: 1 is free, 0 is allocated
        self.sector_map = np.zeros([1280], dtype=np.uint8)
        if segments is not None:
            self.parse_segments(segments)

    def __str__(self):
        return "%s\n (%d free)" % ("\n".join(["track %02d: %s" % (i, line) for i, line in enumerate(str(self.sector_map[self.header.starting_sector_label:(self.header.tracks_per_disk*self.header.sectors_per_track) + self.header.starting_sector_label].reshape([self.header.tracks_per_disk,self.header.sectors_per_track])).splitlines())]), self.num_free_sectors)

    @property
    def num_free_sectors(self):
        free = np.where(self.sector_map == 1)[0]
        return len(free)

    def iter_free_sectors(self):
        for i, pos, size in self.header.iter_sectors():
            if self.sector_map[i] == 1:
                yield i, pos, size

    def parse_segments(self, segments):
        raise errors.NotImplementedError

    def assign_sector_numbers(self, dirent, sector_list):
        """ Map out the sectors and link the sectors together

        raises NotEnoughSpaceOnDisk if the whole file won't fit. It will not
        allow partial writes.
        """
        num = len(sector_list)
        order = self.reserve_space(num)
        if len(order) != num:
            raise errors.InvalidFile("VTOC reserved space for %d sectors. Sectors needed: %d" % (len(order), num))
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
        raise errors.NotImplementedError

    def free_sector_list(self, sector_list):
        for sector in sector_list:
            self.sector_map[sector.sector_num] = 1
        self.calc_bitmap()
