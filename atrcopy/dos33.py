import numpy as np

from errors import *
from diskimages import AtrHeader, DiskImageBase, Directory, VTOC, WriteableSector, BaseSectorList
from segments import DefaultSegment, EmptySegment, ObjSegment, RawTrackSectorSegment, SegmentSaver

import logging
log = logging.getLogger(__name__)


class Dos33VTOC(VTOC):
    def parse_segments(self, segments):
        self.vtoc1 = segments[0].data
        bits = np.unpackbits(self.vtoc1[0x0a:0x64])
        log.debug("vtoc before: %s" % bits)
        self.sector_map[0:720] = bits

    def calc_bitmap(self):
        log.debug("vtoc after: %s" % self.sector_map[0:720])
        packed = np.packbits(self.sector_map[0:720])
        self.vtoc1[0x0a:0x64] = packed
        s = WriteableSector(self.bytes_per_sector, self.vtoc1)
        s.sector_num = 360
        self.sectors.append(s)


class Dos33Directory(Directory):
    @property
    def dirent_class(self):
        return Dos33Dirent

    def get_dirent_sector(self):
        s = self.sector_class(self.bytes_per_sector)
        data = np.zeros([0x0b], dtype=np.uint8)
        s.add_data(data)
        return s

    def encode_empty(self):
        return np.zeros([Dos33Dirent.format.itemsize], dtype=np.uint8)

    def encode_dirent(self, dirent):
        data = dirent.encode_dirent()
        log.debug("encoded dirent: %s" % data)
        return data

    def set_sector_numbers(self, image):
        num = image.get_next_directory_sector(-1)
        for sector in self.sectors:
            sector.sector_num = num
            num = image.get_next_directory_sector(num)
            t, s = image.header.track_from_sector(num)
            sector.data[1] = t
            sector.data[2] = s


class Dos33Dirent(object):
    format = np.dtype([
        ('track', 'u1'),
        ('sector', 'u1'),
        ('flag', 'u1'),
        ('name','S30'),
        ('num_sectors','<u2'),
        ])

    def __init__(self, image, file_num=0, bytes=None):
        self.file_num = file_num
        self.file_type = 0
        self.locked = False
        self.deleted = False
        self.track = 0
        self.sector = 0
        self.filename = ""
        self.num_sectors = 0
        self.is_sane = True
        self.current_sector_index = 0
        self.current_read = 0
        self.sectors_seen = None
        self.sector_map = None
        self.parse_raw_dirent(image, bytes)
    
    def __str__(self):
        flag = self.summary()
        return "File #%-2d (%s) %03d %-30s %03d %03d" % (self.file_num, flag, self.num_sectors, self.filename, self.track, self.sector)
    
    type_map = {
        0x0: "T",
        0x1: "I",
        0x2: "A",
        0x4: "B",
        0x8: "S",
        0x10: "R",
        0x20: "new A",
        0x40: "new B",
    }

    def summary(self):
        locked = "*" if self.locked else " "
        try:
            file_type = self.type_map[self.file_type]
        except KeyError:
            file_type = "?"
        flag = "%s%s" % (locked, file_type)
        return flag
    
    @property
    def verbose_info(self):
        return self.summary

    @property
    def in_use(self):
        return not self.deleted

    @property
    def flag(self):
        return 0xff if self.deleted else self.file_type | (0x80 * int(self.locked))
    
    def parse_raw_dirent(self, image, bytes):
        if bytes is None:
            return
        values = bytes.view(dtype=self.format)[0]
        self.track = values[0]
        if self.track == 0xff:
            self.deleted = True
            self.track = bytes[0x20]
        else:
            self.deleted = False
        self.sector = values[1]
        self.file_type = values[2] & 0x7f
        self.locked = values[2] & 0x80
        self.filename = (bytes[3:0x20] - 0x80).tostring().rstrip()
        self.num_sectors = int(values[4])
        self.is_sane = self.sanity_check(image)

    def encode_dirent(self):
        data = np.zeros([self.format.itemsize], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        values[0] = self.track
        values[1] = self.sector
        values[2] = self.flag
        n = min(len(self.filename), 30)
        data[3:3+n] = np.fromstring(self.filename, dtype=np.uint8) | 0x80
        data[3+n:] = ord(' ') | 0x80
        values[4] = self.num_sectors
        return data

    def mark_deleted(self):
        self.deleted = True
        self.in_use = False

    def update_sector_info(self, sector_list):
        self.num_sectors = sector_list.num_sectors
        self.starting_sector = sector_list.first_sector
    
    def sanity_check(self, image):
        if self.deleted:
            return True
        if self.track == 0:
            return False
        s = image.header.sector_from_track(self.track, self.sector)
        if not image.header.sector_is_valid(s):
            return False
        if self.num_sectors < 0 or self.num_sectors > image.header.max_sectors:
            return False
        return True

    def get_track_sector_list(self, image):
        sector = image.header.sector_from_track(self.track, self.sector)
        sector_list = []
        while sector > 0:
            image.assert_valid_sector(sector)
            print "reading track/sector list", sector
            values, style = image.get_sectors(sector)
            sector = image.header.sector_from_track(values[1], values[2])
            i = 0x0c
            while i < 256:
                t = values[i]
                s = values[i + 1]
                i += 2
                if t == 0:
                    sector = 0
                    break
                sector_list.append(image.header.sector_from_track(t, s))
        self.sector_map = sector_list
    
    def get_sector_list(self, image):
        sector_list = BaseSectorList(image.bytes_per_sector)
        self.start_read(image)
        sector_num = image.header.sector_from_track(self.track, self.sector)
        while sector_num > 0:
            sector = WriteableSector(image.bytes_per_sector, None, sector_num)
            sector_list.append(sector)
            values, style = image.get_sectors(sector_num)
            sector = image.header.sector_from_track(values[1], values[2])
        for sector_num in sector_list:
            sector = WriteableSector(image.bytes_per_sector, None, sector_num)
            sector_list.append(sector)
        return sector_list

    def start_read(self, image):
        if not self.is_sane:
            raise InvalidDirent("Invalid directory entry '%s'" % str(self))
        self.get_track_sector_list(image)
        log.debug("start_read: %s, t/s list: %s" % (str(self), str(self.sector_map)))
        self.current_sector_index = 0
        self.current_read = self.num_sectors
    
    def read_sector(self, image):
        log.debug("read_sector: index=%d in %s" % (self.current_sector_index, str(self)))
        try:
            sector = self.sector_map[self.current_sector_index]
        except IndexError:
            sector = -1
        last = (self.current_sector_index == len(self.sector_map) - 1)
        raw, pos, size = image.get_raw_bytes(sector)
        bytes, num_data_bytes = self.process_raw_sector(image, raw)
        return bytes, last, pos, num_data_bytes

    def process_raw_sector(self, image, raw):
        self.current_sector_index += 1
        num_bytes = len(raw)
        return raw[0:num_bytes], num_bytes
    
    def get_filename(self):
        return self.filename

    def set_values(self, filename, filetype, index):
        self.filename = "%-30s" % filename[0:30]
        self.file_type = self.type_map.get(filetype, 0x04)
        self.locked = False
        self.deleted = False


class Dos33Header(AtrHeader):
    file_format = "DOS 3.3"

    def __init__(self):
        AtrHeader.__init__(self, None, 256, 0)
        self.starting_sector_label = 0
        self.header_offset = 0
        self.sector_order = range(16)
        self.vtoc_sector = 17 * 16
        self.max_sectors = 35 * 16
    
    def __str__(self):
        return "%s Disk Image (size=%d (%dx%db)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)
    
    def __len__(self):
        return 0
    
    def to_array(self):
        raw = np.zeros([0], dtype=np.uint8)
        return raw

    def check_size(self, size):
        AtrHeader.check_size(self, size)
        if size != 143360:
            raise InvalidDiskImage("Incorrect size for DOS 3.3 image")
    
    def sector_is_valid(self, sector):
        # DOS 3.3 sectors count from 0
        return sector >= 0 and sector < self.max_sectors
    
    def get_pos(self, sector):
        if not self.sector_is_valid(sector):
            raise ByteNotInFile166("Sector %d out of range" % sector)
        pos = sector * self.sector_size
        size = self.sector_size
        return pos, size

    def sector_from_track(self, track, sector):
        return track * 16 + sector

    def track_from_sector(self, sector):
        track, sector = divmod(sector, 16)
        return track, sector


class Dos33DiskImage(DiskImageBase):
    def __init__(self, rawdata, filename=""):
        self.first_catalog = 0
        DiskImageBase.__init__(self, rawdata, filename)

    def __str__(self):
        return str(self.header)
    
    def read_header(self):
        self.header = Dos33Header()

    @property
    def bytes_per_sector(self):
        return 256

    @property
    def payload_bytes_per_sector(self):
        return 256

    @property
    def vtoc_class(self):
        return Dos33VTOC

    @property
    def directory_class(self):
        return Dos33Directory
    
    @property
    def raw_sector_class(self):
        return RawTrackSectorSegment

    def get_boot_sector_info(self):
        # based on logic from a2server
        data, style = self.get_sectors(0)
        magic = data[0:4]
        if (magic == [1, 56, 176, 3]).all():
            raise InvalidDiskImage("ProDOS format found; not DOS 3.3 image")
        swap_order = False
        data, style = self.get_sectors(self.header.vtoc_sector)
        if data[3] == 3:
            if data[1] < 35 and data[2] < 16:
                data, style = self.get_sectors(self.header.vtoc_sector + 14)
                if data[2] != 13:
                    swap_order = True
            else:
                raise InvalidDiskImage("Invalid VTOC location for DOS 3.3")

        print "swap", swap_order
    
    vtoc_type = np.dtype([
        ('unused1', 'S1'),
        ('cat_track','u1'),
        ('cat_sector','u1'),
        ('dos_release', 'u1'),
        ('unused2', 'S2'),
        ('vol_num', 'u1'),
        ('unused3', 'S32'),
        ('max_pairs', 'u1'),
        ('unused4', 'S8'),
        ('last_track', 'u1'),
        ('track_dir', 'i1'),
        ('unused5', 'S2'),
        ('num_tracks', 'u1'),
        ('sectors_per_track', 'u1'),
        ('bytes_per_sector', 'u2'),
        ])

    def get_vtoc(self):
        data, style = self.get_sectors(self.header.vtoc_sector)
        values = data[0:56].view(dtype=self.vtoc_type)[0]
        self.first_catalog = self.header.sector_from_track(values[1], values[2])
        self.assert_valid_sector(self.first_catalog)
        self.total_sectors = int(values['num_tracks']) * int(values['sectors_per_track'])
        self.dos_release = values['dos_release']
    
    def get_directory(self, directory=None):
        sector = self.first_catalog
        num = 0
        files = []
        while sector > 0:
            self.assert_valid_sector(sector)
            print "reading catalog sector", sector
            values, style = self.get_sectors(sector)
            sector = self.header.sector_from_track(values[1], values[2])
            i = 0xb
            while i < 256:
                dirent = Dos33Dirent(self, num, values[i:i+0x23])
                if dirent.flag == 0:
                    break
                if not dirent.is_sane:
                    self.all_sane = False
                else:
                    files.append(dirent)
                if directory is not None:
                    directory.set(num, dirent)
                print dirent
                i += 0x23
                num += 1
        self.files = files

    def get_boot_segments(self):
        segments = []
        s = self.get_sector_slice(0, 0)
        r = self.rawdata[s]
        boot1 = ObjSegment(r, 0, 0, 0x800, name="Boot 1")
        s = self.get_sector_slice(1, 9)
        r = self.rawdata[s]
        boot2 = ObjSegment(r, 0, 0, 0x3700, name="Boot 2")
        s = self.get_sector_slice(0x0a, 0x0b)
        r = self.rawdata[s]
        relocator = ObjSegment(r, 0, 0, 0x1b00, name="Relocator")
        s = self.get_sector_slice(0x0c, 0x0c + 25)
        r = self.rawdata[s]
        boot3 = ObjSegment(r, 0, 0, 0x1d00, name="Boot 3")
        return [boot1, boot2, relocator, boot3]
    
    def get_vtoc_segments(self):
        r = self.rawdata
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(self.header.vtoc_sector, 1)
        segment = RawTrackSectorSegment(r[start:start+count], self.header.vtoc_sector, 1, count, 0, 0, self.header.sector_size, name="VTOC")
        segments.append(segment)
        return segments
    
    def get_directory_segments(self):
        byte_order = []
        r = self.rawdata
        segments = []
        sector = self.first_catalog
        while sector > 0:
            self.assert_valid_sector(sector)
            print "reading catalog sector", sector
            raw, pos, size = self.get_raw_bytes(sector)
            byte_order.extend(range(pos, pos + size))
            sector = self.header.sector_from_track(raw[1], raw[2])
        raw = self.rawdata.get_indexed(byte_order)
        segment = DefaultSegment(raw, name="Catalog")
        segments.append(segment)
        return segments

    def get_next_directory_sector(self, sector):
        if sector == -1:
            sector = self.first_catalog
        print "reading catalog sector", sector
        self.assert_valid_sector(sector)
        raw, _, _ = self.get_raw_bytes(sector)
        next_sector = self.header.sector_from_track(raw[1], raw[2])
        if next_sector == 0:
            raise NoSpaceInDirectory("No space left in catalog")
        return next_sector
    
    def get_file_segment(self, dirent):
        byte_order = []
        dirent.start_read(self)
        while True:
            bytes, last, pos, size = dirent.read_sector(self)
            byte_order.extend(range(pos, pos + size))
            if last:
                break
        if len(byte_order) > 0:
            name = "%s %ds@%d" % (dirent.get_filename(), dirent.num_sectors, dirent.sector_map[0])
            verbose_name = "%s (%d sectors, first@%d) %s" % (dirent.get_filename(), dirent.num_sectors, dirent.sector_map[0], dirent.verbose_info)
            raw = self.rawdata.get_indexed(byte_order)
            segment = DefaultSegment(raw, name=name, verbose_name=verbose_name)
        else:
            segment = EmptySegment(self.rawdata, name=dirent.get_filename())
        return segment


class ProdosHeader(Dos33Header):
    file_format = "ProDOS"


class ProdosDiskImage(Dos33DiskImage):
    def read_header(self):
        self.header = ProdosHeader()

    def get_boot_sector_info(self):
        # based on logic from a2server
        data, style = self.get_sectors(0)
        magic = data[0:4]
        swap_order = False
        if (magic == [1, 56, 176, 3]).all():
            data, style = self.get_sectors(1)
            prodos = data[3:9].tostring()
            if prodos == "PRODOS":
                pass
            else:
                data, style = self.get_sectors(14)
                prodos = data[3:9].tostring()
                if prodos == "PRODOS":
                    swap_order = True
                else:
                    raise InvalidDiskImage("No ProDOS header info found")
