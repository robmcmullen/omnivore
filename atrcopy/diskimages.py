import numpy as np

from errors import *
from segments import SegmentData, EmptySegment, ObjSegment, RawSectorsSegment
from utils import to_numpy

import logging
log = logging.getLogger(__name__)


class AtrHeader(object):
    # ATR Format described in http://www.atarimax.com/jindroush.atari.org/afmtatr.html
    format = np.dtype([
        ('wMagic', '<u2'),
        ('wPars', '<u2'),
        ('wSecSize', '<u2'),
        ('btParsHigh', 'u1'),
        ('dwCRC','<u4'),
        ('unused','<u4'),
        ('btFlags','u1'),
        ])
    file_format = "ATR"
    
    def __init__(self, bytes=None, sector_size=128, initial_sectors=3, create=False):
        self.image_size = 0
        self.sector_size = sector_size
        self.crc = 0
        self.unused = 0
        self.flags = 0
        self.header_offset = 0
        self.starting_sector_label = 1
        self.initial_sector_size = sector_size
        self.num_initial_sectors = initial_sectors
        self.max_sectors = 0
        if create:
            self.header_offset = 16
            self.check_size(0)
        if bytes is None:
            return
        
        if len(bytes) == 16:
            values = bytes.view(dtype=self.format)[0]
            if values[0] != 0x296:
                raise InvalidAtrHeader
            self.image_size = (int(values[3]) * 256 * 256 + int(values[1])) * 16
            self.sector_size = int(values[2])
            self.crc = int(values[4])
            self.unused = int(values[5])
            self.flags = int(values[6])
            self.header_offset = 16
        else:
            raise InvalidAtrHeader
    
    def __str__(self):
        return "%s Disk Image (size=%d (%dx%db), crc=%d flags=%d unused=%d)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size, self.crc, self.flags, self.unused)
    
    def __len__(self):
        return self.header_offset
    
    def to_array(self):
        raw = np.zeros([16], dtype=np.uint8)
        values = raw.view(dtype=self.format)[0]
        values[0] = 0x296
        paragraphs = self.image_size / 16
        parshigh, pars = divmod(paragraphs, 256*256)
        values[1] = pars
        values[2] = self.sector_size
        values[3] = parshigh
        values[4] = self.crc
        values[5] = self.unused
        values[6] = self.flags
        return raw

    def check_size(self, size):
        if size == 92160 or size == 92176:
            self.image_size = 92160
            self.sector_size = 128
            self.initial_sector_size = 0
            self.num_initial_sectors = 0
        elif size == 184320 or size == 184336:
            self.image_size = 184320
            self.sector_size = 256
            self.initial_sector_size = 0
            self.num_initial_sectors = 0
        elif size == 183936 or size == 183952:
            self.image_size = 183936
            self.sector_size = 256
            self.initial_sector_size = 128
            self.num_initial_sectors = 3
        else:
            self.image_size = size
        initial_bytes = self.initial_sector_size * self.num_initial_sectors
        self.max_sectors = ((self.image_size - initial_bytes) / self.sector_size) + self.num_initial_sectors

    def strict_check(self, image):
        pass
    
    def sector_is_valid(self, sector):
        return sector > 0 and sector <= self.max_sectors
    
    def get_pos(self, sector):
        if not self.sector_is_valid(sector):
            raise ByteNotInFile166("Sector %d out of range" % sector)
        if sector <= self.num_initial_sectors:
            pos = self.num_initial_sectors * (sector - 1)
            size = self.initial_sector_size
        else:
            pos = self.num_initial_sectors * self.initial_sector_size + (sector - 1 - self.num_initial_sectors) * self.sector_size
            size = self.sector_size
        pos += self.header_offset
        return pos, size


class XfdHeader(AtrHeader):
    file_format = "XFD"
    
    def __str__(self):
        return "%s Disk Image (size=%d (%dx%db)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)
    
    def __len__(self):
        return 0
    
    def to_array(self):
        raw = np.zeros([0], dtype=np.uint8)
        return raw

    def strict_check(self, image):
        size = len(image)
        if size in [92160, 133120, 183936, 184320]:
            return
        raise InvalidDiskImage("Uncommon size of XFD file")


class DiskImageBase(object):
    def __init__(self, rawdata, filename=""):
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
        self.setup()

    def __len__(self):
        return len(self.rawdata)

    @property
    def bytes_per_sector(self):
        raise NotImplementedError

    @property
    def payload_bytes_per_sector(self):
        raise NotImplementedError

    @property
    def writeable_sector_class(self):
        return WriteableSector

    @property
    def vtoc_class(self):
        return VTOC

    @property
    def directory_class(self):
        return Directory

    @property
    def sector_list_class(self):
        return SectorList
    
    def set_filename(self, filename):
        if "." in filename:
            self.filename, self.ext = filename.rsplit(".", 1)
        else:
            self.filename, self.ext = filename, ""
    
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
        if format.lower() == "atr":
            header = AtrHeader(create=True)
            header.check_size(diskimage.size)
        else:
            raise RuntimeError("Unknown header type %s" % format)
        return header
    
    def as_new_format(self, format="ATR"):
        """ Create a new disk image in the specified format
        """
        first_data = len(self.header)
        raw = self.rawdata[first_data:]
        data = add_atr_header(raw)
        newraw = SegmentData(data)
        image = self.__class__(newraw)
        return image
    
    def save(self, filename=""):
        if not filename:
            filename = self.filename
            if self.ext:
                filename += "." + self.ext
        if not filename:
            raise RuntimeError("No filename specified for save!")
        bytes = self.bytes[:]
        with open(filename, "wb") as fh:
            bytes.tofile(fh)
    
    def assert_valid_sector(self, sector):
        if not self.header.sector_is_valid(sector):
            raise ByteNotInFile166("Sector %d out of range" % sector)
    
    def check_sane(self):
        if not self.all_sane:
            raise InvalidDiskImage("Invalid directory entries; may be boot disk")
    
    def read_header(self):
        bytes = self.bytes[0:16]
        try:
            self.header = AtrHeader(bytes)
        except InvalidAtrHeader:
            self.header = XfdHeader()
    
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
        self.segments.append(RawSectorsSegment(r[i:], self.header.starting_sector_label, self.header.max_sectors, self.header.image_size, self.header.initial_sector_size, self.header.num_initial_sectors, self.header.sector_size, name="Raw disk sectors"))
        self.segments.extend(self.get_boot_segments())
        self.segments.extend(self.get_vtoc_segments())
        self.segments.extend(self.get_directory_segments())
        self.segments.extend(self.get_file_segments())
    
    boot_record_type = np.dtype([
        ('BFLAG', 'u1'),
        ('BRCNT', 'u1'),
        ('BLDADR', '<u2'),
        ('BWTARR', '<u2'),
        ])
    
    def get_boot_segments(self):
        data, style = self.get_sectors(1)
        values = data[0:6].view(dtype=self.boot_record_type)[0]  
        flag = int(values[0])
        segments = []
        if flag == 0:
            num = int(values[1])
            addr = int(values[2])
            s = self.get_sector_slice(1, num)
            r = self.rawdata[s]
            header = ObjSegment(r[0:6], 0, 0, addr, addr + 6, name="Boot Header")
            sectors = ObjSegment(r, 0, 0, addr, addr + len(r), name="Boot Sectors")
            code = ObjSegment(r[6:], 0, 0, addr + 6, addr + len(r), name="Boot Code")
            segments = [sectors, header, code]
        return segments
    
    def get_vtoc_segments(self):
        return []

    def get_directory_segments(self):
        return []
    
    def find_dirent(self, filename):
        for dirent in self.files:
            if filename == dirent.get_filename():
                return dirent
        raise FileNotFound("%s not found on disk" % filename)
    
    def find_file(self, filename):
        dirent = self.find_dirent(filename)
        return self.get_file(dirent)
    
    def get_file(self, dirent):
        segment = self.get_file_segment(dirent)
        return segment.tostring()
    
    def get_file_segment(self, dirent):
        pass
    
    def get_file_segments(self):
        segments = []
        for dirent in self.files:
            try:
                segment = self.get_file_segment(dirent)
            except InvalidFile, e:
                segment = EmptySegment(self.rawdata, name=dirent.get_filename(), error=str(e))
            segments.append(segment)
        return segments

    # file writing methods

    def begin_transaction(self):
        state = self.bytes[:], self.style[:]
        return state

    def rollback_transaction(self, state):
        self.bytes[:], self.style[:] = state
        return

    def write_file(self, filename, filetype, data):
        """Write data to a file on disk

        This throws various exceptions on failures, for instance if there is
        not enough space on disk or a free entry is not available in the
        catalog.
        """
        state = self.begin_transaction()
        try:
            directory = self.directory_class(self.bytes_per_sector)
            self.get_directory(directory)
            dirent = directory.add_dirent(filename, filetype)
            data = to_numpy(data)
            sector_list = self.sector_list_class(self.bytes_per_sector, self.payload_bytes_per_sector, data, self.writeable_sector_class)
            vtoc_segments = self.get_vtoc_segments()
            vtoc = self.vtoc_class(self.bytes_per_sector, vtoc_segments)
            directory.save_dirent(dirent, vtoc, sector_list)
            self.write_sector_list(sector_list)
            self.write_sector_list(vtoc)
            self.write_sector_list(directory)
            self.get_metadata()
        except AtrError:
            self.rollback_transaction(state)
            raise
        finally:
            self.get_metadata()

    def write_sector_list(self, sector_list):
        for sector in sector_list:
            pos, size = self.header.get_pos(sector.sector_num)
            log.debug("writing: %s" % sector)
            self.bytes[pos:pos + size] = sector.data

    def delete_file(self, filename):
        state = self.begin_transaction()
        try:
            directory = self.directory_class(self.bytes_per_sector)
            self.get_directory(directory)
            dirent = directory.find_dirent(filename)
            sector_list = dirent.get_sector_list(self)
            vtoc_segments = self.get_vtoc_segments()
            vtoc = self.vtoc_class(self.bytes_per_sector, vtoc_segments)
            directory.remove_dirent(dirent, vtoc, sector_list)
            self.write_sector_list(sector_list)
            self.write_sector_list(vtoc)
            self.write_sector_list(directory)
            self.get_metadata()
        except AtrError:
            self.rollback_transaction(state)
            raise
        finally:
            self.get_metadata()


class WriteableSector(object):
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


class BaseSectorList(object):
    def __init__(self, bytes_per_sector):
        self.bytes_per_sector = bytes_per_sector
        self.sectors = []

    def __len__(self):
        return len(self.sectors)

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

    def append(self, sector):
        self.sectors.append(sector)


class Directory(BaseSectorList):
    def __init__(self, bytes_per_sector, num_dirents=-1, sector_class=WriteableSector):
        BaseSectorList.__init__(self, bytes_per_sector)
        self.sector_class = sector_class
        self.num_dirents = num_dirents
        # number of dirents may be unlimited, so use a dict instead of a list
        self.dirents = {}

    def set(self, index, dirent):
        self.dirents[index] = dirent
        log.debug("set dirent #%d: %s" % (index, dirent))

    def get_free_dirent(self):
        used = set()
        d = self.dirents.items()
        d.sort()
        for i, dirent in d:
            if not dirent.in_use:
                return i
            used.add(i)
        if self.num_dirents > 0 and (len(used) >= self.num_dirents):
            raise NoSpaceInDirectory()
        i += 1
        used.add(i)
        return i

    def add_dirent(self, filename, filetype):
        index = self.get_free_dirent()
        dirent = self.dirent_class(None)
        dirent.set_values(filename, filetype, index)
        self.set(index, dirent)
        return dirent

    def find_dirent(self, filename):
        for dirent in self.dirents.values():
            if filename == dirent.get_filename():
                return dirent
        raise FileNotFound("%s not found on disk" % filename)

    def save_dirent(self, dirent, vtoc, sector_list):
        self.place_sector_list(dirent, vtoc, sector_list)
        dirent.update_sector_info(sector_list)
        self.calc_sectors()

    def place_sector_list(self, dirent, vtoc, sector_list):
        """ Map out the sectors and link the sectors together

        raises NotEnoughSpaceOnDisk if the whole file won't fit. It will not
        allow partial writes.
        """
        sector_list.calc_extra_sectors()
        num = len(sector_list)
        order = vtoc.reserve_space(num)
        if len(order) != num:
            raise InvalidFile("VTOC reserved space for %d sectors. Sectors needed: %d" % (len(order), num))
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

    def remove_dirent(self, dirent, vtoc, sector_list):
        vtoc.free_sector_list(sector_list)
        dirent.mark_deleted()
        self.calc_sectors()

    @property
    def dirent_class(self):
        raise NotImplementedError

    def calc_sectors(self):
        self.sectors = []
        self.current_sector = self.sector_class(self.bytes_per_sector)
        self.encode_index = 0

        d = self.dirents.items()
        d.sort()
        # there may be gaps, so fill in missing entries with blanks
        current = 0
        for index, dirent in d:
            for missing in range(current, index):
                log.debug("Encoding empty dirent at %d" % missing)
                data = self.encode_empty()
                self.store_encoded(data)
            log.debug("Encoding dirent: %s" % dirent)
            data = self.encode_dirent(dirent)
            self.store_encoded(data)
            current = index + 1
        self.finish_encoding()

    def encode_empty(self):
        raise NotImplementedError

    def encode_dirent(self, dirent):
        raise NotImplementedError

    def store_encoded(self, data):
        while True:
            log.debug("store_encoded: %d bytes in %s" % (len(data), self.current_sector))
            data = self.current_sector.add_data(data)
            if len(data) > 0:
                self.sectors.append(self.current_sector)
                self.current_sector = self.sector_class(self.bytes_per_sector)
            else:
                break

    def finish_encoding(self):
        if not self.current_sector.is_empty:
            self.sectors.append(self.current_sector)
        self.set_sector_numbers()

    def set_sector_numbers(self):
        raise NotImplementedError


class VTOC(BaseSectorList):
    def __init__(self, bytes_per_sector, segments=None):
        BaseSectorList.__init__(self, bytes_per_sector)

        # sector map: 1 is free, 0 is allocated
        self.sector_map = np.zeros([1280], dtype=np.uint8)
        if segments is not None:
            self.parse_segments(segments)

    def parse_segments(self, segments):
        raise NotImplementedError

    def reserve_space(self, num):
        order = []
        for i in range(num):
            order.append(self.get_next_free_sector())
        log.debug("Sectors reserved: %s" % order)
        self.calc_bitmap()
        return order

    def get_next_free_sector(self):
        free = np.nonzero(self.sector_map)[0]
        if len(free) > 0:
            num = free[0]
            log.debug("Found sector %d free" % num)
            self.sector_map[num] = 0
            return num
        raise NotEnoughSpaceOnDisk("No space left in VTOC")

    def calc_bitmap(self):
        raise NotImplementedError

    def free_sector_list(self, sector_list):
        for sector in sector_list:
            self.sector_map[sector.sector_num] = 1


class SectorList(BaseSectorList):
    def __init__(self, bytes_per_sector, usable, data, sector_class):
        BaseSectorList.__init__(self, bytes_per_sector)
        self.data = to_numpy(data)
        self.usable_bytes = usable
        self.split_into_sectors(sector_class)
        self.file_length = -1

    def split_into_sectors(self, sector_class):
        index = 0
        while index < len(self.data):
            count = min(self.usable_bytes, len(self.data) - index)
            sector = sector_class(self.bytes_per_sector, self.data[index:index + count])
            self.sectors.append(sector)
            index += count


    def calc_extra_sectors(self):
        """ Add extra sectors to the list.

        For example, DOS 3.3 uses a track/sector list at the beginning of the
        file
        """
        pass



class BootDiskImage(DiskImageBase):
    def __str__(self):
        return "%s Boot Disk" % (self.header)
    
    def check_size(self):
        if self.header is None:
            return
        start, size = self.header.get_pos(1)
        b = self.bytes
        i = self.header.header_offset
        flag = b[i:i + 2].view(dtype='<u2')[0]
        if flag == 0xffff:
            raise InvalidDiskImage("Appears to be an executable")
        nsec = b[i + 1]
        bload = b[i + 2:i + 4].view(dtype='<u2')[0]
        
        # Sanity check: number of sectors to be loaded can't be more than the
        # lower 48k of ram because there's no way to bank switch or anything
        # before the boot sectors are finished loading
        max_ram = 0xc000
        max_size = max_ram - bload
        max_sectors = max_size / self.header.sector_size
        if nsec > max_sectors or nsec < 1:
            raise InvalidDiskImage("Number of boot sectors out of range")
        if bload < 0x200 or bload > (0xc000 - (nsec * self.header.sector_size)):
            raise InvalidDiskImage("Bad boot load address")

def add_atr_header(bytes):
    header = AtrHeader(create=True)
    header.check_size(len(bytes))
    hlen = len(header)
    data = np.empty([hlen + len(bytes)], dtype=np.uint8)
    data[0:hlen] = header.to_array()
    data[hlen:] = bytes
    return data
