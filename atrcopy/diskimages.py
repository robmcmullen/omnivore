import numpy as np

from . import errors
from .segments import SegmentData, EmptySegment, ObjSegment, RawSectorsSegment
from .utils import *
from .executables import create_executable_file_data

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class BaseHeader:
    file_format = "generic"  # text descriptor of file format
    sector_class = WriteableSector

    def __init__(self, sector_size=256, initial_sectors=0, vtoc_sector=0, starting_sector_label=0, create=False):
        self.image_size = 0
        self.sector_size = sector_size
        self.payload_bytes = sector_size
        self.initial_sector_size = 0
        self.num_initial_sectors = 0
        self.crc = 0
        self.unused = 0
        self.flags = 0
        self.header_offset = 0
        self.starting_sector_label = starting_sector_label
        self.max_sectors = 0  # number of sectors, -1 is unlimited
        self.tracks_per_disk = 0
        self.sectors_per_track = 0
        self.first_vtoc = vtoc_sector
        self.num_vtoc = 1
        self.extra_vtoc = []
        self.first_directory = 0
        self.num_directory = 0

    def __len__(self):
        return self.header_offset

    def to_array(self):
        header_bytes = np.zeros([self.header_offset], dtype=np.uint8)
        self.encode(header_bytes)
        return header_bytes

    def encode(self, header_bytes):
        """Subclasses should override this to put the byte values into the
        header.
        """
        return

    def sector_is_valid(self, sector):
        return (self.max_sectors < 0) | (sector >= self.starting_sector_label and sector < (self.max_sectors + self.starting_sector_label))

    def iter_sectors(self):
        i = self.starting_sector_label
        while self.sector_is_valid(i):
            pos, size = self.get_pos(i)
            yield i, pos, size
            i += 1

    def get_pos(self, sector):
        """Get index (into the raw data of the disk image) of start of sector

        This base class method assumes the sectors are one after another, in
        order starting from the beginning of the raw data.
        """
        if not self.sector_is_valid(sector):
            raise ByteNotInFile166("Sector %d out of range" % sector)
        pos = sector * self.sector_size + self.header_offset
        size = self.sector_size
        return pos, size

    def sector_from_track(self, track, sector):
        return (track * self.sectors_per_track) + sector

    def track_from_sector(self, sector):
        track, sector = divmod(sector, self.sectors_per_track)
        return track, sector

    def check_size(self, size):
        raise errors.InvalidDiskImage("BaseHeader subclasses need custom checks for size")

    def strict_check(self, image):
        pass

    def create_sector(self, data=None):
        if data is None:
            data = np.zeros([self.sector_size], dtype=np.uint8)
        return self.sector_class(self.sector_size, data)


class DiskImageBase:
    default_executable_extension = None

    def __init__(self, rawdata, filename="", create=False):
        self.rawdata = rawdata
        self.bytes = self.rawdata.get_data()
        self.style = self.rawdata.get_style()
        self.size = np.alen(self.bytes)
        self.set_filename(filename)
        self.header = None
        self.total_sectors = 0
        self.unused_sectors = 0
        self.files = [] # all dirents that show up in a normal dir listing
        self.segments = []
        self.all_sane = True
        self.default_filetype = ""
        if create:
            self.header = self.new_header(self)
        else:
            self.setup()

    def __len__(self):
        return len(self.rawdata)

    @property
    def writeable_sector_class(self):
        return WriteableSector

    @property
    def raw_sector_class(self):
        return RawSectorsSegment

    @property
    def vtoc_class(self):
        return VTOC

    @property
    def directory_class(self):
        return Directory

    def set_filename(self, filename):
        if '.' in filename:
            self.filename, self.ext = filename.rsplit('.', 1)
        else:
            self.filename, self.ext = filename, ''

    def dir(self):
        lines = []
        lines.append(str(self))
        for dirent in self.files:
            if dirent.in_use:
                lines.append(str(dirent))
        return "\n".join(lines)

    def setup(self):
        self.size = np.alen(self.bytes)
        self.read_header()
        self.header.check_size(self.size - len(self.header))
        self.check_size()
        self.get_metadata()

    def get_metadata(self):
        self.get_boot_sector_info()
        self.get_vtoc()
        self.get_directory()
        self.check_sane()

    def strict_check(self):
        """Perform the strictest of checks to verify the data is valid """
        self.header.strict_check(self)

    def relaxed_check(self):
        """Conform as much as possible to get the data to work with this
        format.
        """
        pass

    @classmethod
    def new_header(cls, diskimage, format="ATR"):
        raise errors.NotImplementedError

    def as_new_format(self, format="ATR"):
        """ Create a new disk image in the specified format
        """
        raise errors.NotImplementedError

    def save(self, filename=""):
        if not filename:
            filename = self.filename
            if self.ext:
                filename += '.' + self.ext
        if not filename:
            raise RuntimeError("No filename specified for save!")
        data = self.bytes[:]
        with open(filename, "wb") as fh:
            data.tofile(fh)

    def assert_valid_sector(self, sector):
        if not self.header.sector_is_valid(sector):
            raise errors.ByteNotInFile166("Sector %d out of range" % sector)

    def check_sane(self):
        if not self.all_sane:
            raise errors.InvalidDiskImage("Invalid directory entries; may be boot disk")

    def read_header(self):
        return BaseHeader()

    def check_size(self):
        pass

    def get_boot_sector_info(self):
        pass

    def get_vtoc(self):
        """Get information from VTOC and populate the VTOC object"""
        pass

    def get_directory(self, directory=None):
        pass

    def get_raw_bytes(self, sector):
        pos, size = self.header.get_pos(sector)
        return self.bytes[pos:pos + size], pos, size

    def get_sector_slice(self, start, end=None):
        """ Get contiguous sectors
        
        :param start: first sector number to read (note: numbering starts from 1)
        :param end: last sector number to read
        :returns: bytes
        """
        pos, size = self.header.get_pos(start)
        if end is None:
            end = start
        while start < end:
            start += 1
            _, more = self.header.get_pos(start)
            size += more
        return slice(pos, pos + size)

    def get_sectors(self, start, end=None):
        """ Get contiguous sectors
        
        :param start: first sector number to read (note: numbering starts from 1)
        :param end: last sector number to read
        :returns: bytes
        """
        s = self.get_sector_slice(start, end)
        return self.bytes[s], self.style[s]

    def get_contiguous_sectors(self, sector, num):
        start = 0
        count = 0
        for index in range(sector, sector + num):
            pos, size = self.header.get_pos(index)
            if start == 0:
                start = pos
            count += size
        return start, count

    def parse_segments(self):
        r = self.rawdata
        i = self.header.header_offset
        if self.header.image_size > 0:
            self.segments.append(ObjSegment(r[0:i], 0, 0, 0, i, name="%s Header" % self.header.file_format))
        self.segments.append(self.raw_sector_class(r[i:], self.header.starting_sector_label, self.header.max_sectors, self.header.image_size, self.header.initial_sector_size, self.header.num_initial_sectors, self.header.sector_size, name="Raw disk sectors"))
        self.segments.extend(self.get_boot_segments())
        self.segments.extend(self.get_vtoc_segments())
        self.segments.extend(self.get_directory_segments())
        self.segments.extend(self.get_file_segments())

    def get_boot_segments(self):
        return []

    def get_vtoc_segments(self):
        return []

    def get_directory_segments(self):
        return []

    def find_dirent(self, filename):
        # check if we've been passed a dirent instead of a filename
        if hasattr(filename, "filename"):
            return filename
        for dirent in self.files:
            if filename == dirent.filename:
                return dirent
        raise errors.FileNotFound("%s not found on disk" % str(filename))

    def find_file(self, filename):
        dirent = self.find_dirent(filename)
        return self.get_file(dirent)

    def get_file(self, dirent):
        segment = self.get_file_segment(dirent)
        return segment.tobytes()

    def get_file_segment(self, dirent):
        pass

    def get_file_segments(self):
        segments = []
        for dirent in self.files:
            try:
                segment = self.get_file_segment(dirent)
            except errors.InvalidFile as e:
                segment = EmptySegment(self.rawdata, name=dirent.filename, error=str(e))
            segments.append(segment)
        return segments

    def create_executable_file_image(self, output_name, segments, run_addr=None):
        try:
            data, filetype = create_executable_file_data(output_name, segments, run_addr)
        except errors.UnsupportedContainer:
            data, filetype = create_executable_file_data(self.default_executable_extension, segments, run_addr)
        return data, filetype

    @classmethod
    def create_boot_image(self, segments, run_addr=None):
        raise errors.NotImplementedError

    # file writing methods

    def begin_transaction(self):
        state = self.bytes[:], self.style[:]
        return state

    def rollback_transaction(self, state):
        self.bytes[:], self.style[:] = state
        return

    def get_vtoc_object(self):
        vtoc_segments = self.get_vtoc_segments()
        vtoc = self.vtoc_class(self.header, vtoc_segments)
        return vtoc

    def write_file(self, filename, filetype, data):
        """Write data to a file on disk

        This throws various exceptions on failures, for instance if there is
        not enough space on disk or a free entry is not available in the
        catalog.
        """
        state = self.begin_transaction()
        try:
            directory = self.directory_class(self.header)
            self.get_directory(directory)
            dirent = directory.add_dirent(filename, filetype)
            data = to_numpy(data)
            sector_list = self.build_sectors(data)
            vtoc = self.get_vtoc_object()
            directory.save_dirent(self, dirent, vtoc, sector_list)
            self.write_sector_list(sector_list)
            self.write_sector_list(vtoc)
            self.write_sector_list(directory)
        except errors.AtrError:
            self.rollback_transaction(state)
            raise
        finally:
            self.get_metadata()

    def build_sectors(self, data):
        data = to_numpy(data)
        sectors = BaseSectorList(self.header)
        index = 0
        while index < len(data):
            count = min(self.header.payload_bytes, len(data) - index)
            sector = self.header.create_sector(data[index:index + count])
            sectors.append(sector)
            index += count
        return sectors

    def write_sector_list(self, sector_list):
        for sector in sector_list:
            pos, size = self.header.get_pos(sector.sector_num)
            if _xd: log.debug("writing: %s at %d" % (sector, pos))
            self.bytes[pos:pos + size] = sector.data

    def delete_file(self, filename):
        state = self.begin_transaction()
        try:
            directory = self.directory_class(self.header)
            self.get_directory(directory)
            dirent = directory.find_dirent(filename)
            sector_list = dirent.get_sectors_in_vtoc(self)
            vtoc = self.get_vtoc_object()
            directory.remove_dirent(self, dirent, vtoc, sector_list)
            self.write_sector_list(vtoc)
            self.write_sector_list(directory)
        except errors.AtrError:
            self.rollback_transaction(state)
            raise
        finally:
            self.get_metadata()

    def shred(self, fill_value=0):
        state = self.begin_transaction()
        try:
            vtoc = self.get_vtoc_object()
            for sector_num, pos, size in vtoc.iter_free_sectors():
                if _xd: log.debug("shredding: sector %s at %d, fill value=%d" % (sector_num, pos, fill_value))
                self.bytes[pos:pos + size] = fill_value
        except errors.AtrError:
            self.rollback_transaction(state)
            raise
        finally:
            self.get_metadata()
