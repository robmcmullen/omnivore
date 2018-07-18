import numpy as np

from . import errors
from .diskimages import BaseHeader, DiskImageBase
from .utils import Directory, VTOC, WriteableSector, BaseSectorList, Dirent
from .segments import DefaultSegment, EmptySegment, ObjSegment, RawTrackSectorSegment, SegmentSaver, get_style_bits, SegmentData
from .executables import get_bsave

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class Dos33TSSector(WriteableSector):
    def __init__(self, header, sector_list=None, start=None, end=None, data=None):
        WriteableSector.__init__(self, header.sector_size, data)
        self.header = header
        self.used = header.sector_size
        if data is None:
            self.set_tslist(sector_list, start, end)

    def set_tslist(self, sector_list, start, end):
        index = 0xc
        for i in range(start, end):
            sector = sector_list[i]
            t, s = self.header.track_from_sector(sector.sector_num)
            self.data[index] = t
            self.data[index + 1] = s
            if _xd: log.debug("tslist entry #%d: %d, %d" % (index, t, s))
            index += 2

    def get_tslist(self):
        index = 0xc
        sector_list = []
        while index < self.header.sector_size:
            t = self.data[index]
            s = self.data[index + 1]
            sector_list.append(self.header.sector_from_track(t, s))
            index += 2
        return sector_list

    @property
    def next_sector_num(self):
        t = self.data[1]
        s = self.data[2]
        return self.header.sector_from_track(t, s)

    @next_sector_num.setter
    def next_sector_num(self, value):
        self._next_sector_num = value
        t, s = self.header.track_from_sector(value)
        self.data[1] = t
        self.data[2] = s


class Dos33VTOC(VTOC):
    max_tracks = (256 - 0x38) // 4  # 50, but kept here in case sector size changed
    max_sectors = max_tracks * 16
    vtoc_bit_reorder_index = np.tile(np.arange(15, -1, -1), max_tracks) + (np.repeat(np.arange(max_tracks), 16) * 16)

    def parse_segments(self, segments):
        # VTOC stored in groups of 4 bytes starting at 0x38
        # in bits, the sector used data is stored by track:
        #
        # FEDCBA98 76543210 xxxxxxxx xxxxxxxx
        #
        # where the x values are ignored (should be zeros). Track 0 info is
        # found starting at 0x38, track 1 is found at 0x3c, etc.
        #
        # Want to convert this to an array that is a list of bits by
        # track/sector number, i.e.:
        #
        # t0s0 t0s1 t0s2 t0s3 t0s4 t0s5 t0s6 t0s7 ... t1s0 t1s1 ... etc
        #
        # Problem: the bits are stored backwards, so a straight unpackbits will
        # produce:
        #
        # t0sf t0se t0sd ...
        #
        # i.e. each group of 16 bits needs to be reversed.
        self.vtoc = segments[0].data

        # create a view starting at 0x38 where out of every 4 bytes, the first
        # two are used and the second 2 are skipped. Regular slicing doesn't
        # work like this, so thanks to stackoverflow.com/questions/33801170,
        # reshaping it to a 2d array with 4 elements in each row, doing a slice
        # *there* to skip the last 2 entries in each row, then flattening it
        # gives us what we need.
        usedbytes = self.vtoc[0x38:].reshape((-1, 4))[:,:2].flatten()

        # The bits here are still ordered backwards for each track, e.g. F E D
        # C B A 9 8 7 6 5 4 3 2 1 0
        bits = np.unpackbits(usedbytes)

        # so we need to reorder them using numpy's indexing before stuffing
        # them into the sector map
        self.sector_map[0:self.max_sectors] = bits[self.vtoc_bit_reorder_index]
        if _xd: log.debug("vtoc before:\n%s" % str(self))  # expensive debugging call

    def calc_bitmap(self):
        if _xd: log.debug("vtoc after:\n%s" % str(self))  # expensive debugging call

        # reverse the process from above, so swap the order of every 16 bits,
        # turn them into bytes, then stuff them back into the vtoc. The bit
        # reorder list is commutative, so we don't need another order here.
        packed = np.packbits(self.sector_map[self.vtoc_bit_reorder_index])
        vtoc = self.vtoc[0x38:].reshape((-1, 4))
        packed = packed.reshape((-1, 2))
        vtoc[:,:2] = packed[:,:]

        # FIXME
        self.vtoc[0x38:] = vtoc.flatten()
        s = WriteableSector(self.sector_size, self.vtoc)
        s.sector_num = 17 * 16
        self.sectors.append(s)


class Dos33Directory(Directory):
    @property
    def dirent_class(self):
        return Dos33Dirent

    def get_dirent_sector(self):
        s = self.sector_class(self.sector_size)
        data = np.zeros([0x0b], dtype=np.uint8)
        s.add_data(data)
        return s

    def encode_empty(self):
        return np.zeros([Dos33Dirent.format.itemsize], dtype=np.uint8)

    def encode_dirent(self, dirent):
        data = dirent.encode_dirent()
        if _xd: log.debug("encoded dirent: %s" % data)
        return data

    def set_sector_numbers(self, image):
        current_sector = -1
        for sector in self.sectors:
            current_sector, next_sector = image.get_directory_sector_links(current_sector)
            sector.sector_num = current_sector
            t, s = image.header.track_from_sector(next_sector)
            sector.data[1] = t
            sector.data[2] = s
            if _xd: log.debug("directory sector %d -> next = %d" % (sector.sector_num, next_sector))
            current_sector = next_sector


class Dos33Dirent(Dirent):
    format = np.dtype([
        ('track', 'u1'),
        ('sector', 'u1'),
        ('flag', 'u1'),
        ('name','S30'),
        ('num_sectors','<u2'),
        ])

    def __init__(self, image, file_num=0, bytes=None):
        Dirent.__init__(self, file_num)
        self._file_type = 0
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
        return "File #%-2d (%s) %03d %-30s %03d %03d" % (self.file_num, self.summary, self.num_sectors, self.filename, self.track, self.sector)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.filename == other.filename and self.track == other.track and self.sector == other.sector and self.num_sectors == other.num_sectors

    type_to_text = {
        0x0: "T",  # text
        0x1: "I",  # integer basic
        0x2: "A",  # applesoft basic
        0x4: "B",  # binary
        0x8: "S",  # ?
        0x10: "R",  # relocatable object module
        0x20: "a",  # ?
        0x40: "b",  # ?
    }
    text_to_type = {v: k for k, v in type_to_text.items()}

    @property
    def file_type(self):
        """User friendly version of file type, not the binary number"""
        return self.type_to_text.get(self._file_type, "?")

    @property
    def summary(self):
        if self.deleted:
            locked = "D"
            file_type = " "
        else:
            locked = "*" if self.locked else " "
            file_type = self.file_type
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
        return 0xff if self.deleted else self._file_type | (0x80 * int(self.locked))

    def extra_metadata(self, image):
        lines = []
        ts = self.get_track_sector_list(image)
        lines.append("track/sector list at: " + str(ts))
        lines.append("sector map: " + str(self.sector_map))
        return "\n".join(lines)

    def parse_raw_dirent(self, image, data):
        if data is None:
            return
        values = data.view(dtype=self.format)[0]
        self.track = values[0]
        if self.track == 0xff:
            self.deleted = True
            self.track = data[0x20]
        else:
            self.deleted = False
        self.sector = values[1]
        self._file_type = values[2] & 0x7f
        self.locked = values[2] & 0x80
        self.filename = (data[3:0x20] - 0x80).tobytes().rstrip().decode("ascii", errors='ignore')
        self.num_sectors = int(values[4])
        self.is_sane = self.sanity_check(image)

    def encode_dirent(self):
        data = np.zeros([self.format.itemsize], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        values[0] = 0xff if self.deleted else self.track
        values[1] = self.sector
        values[2] = self.flag
        n = min(len(self.filename), 30)
        data[3:3+n] = np.fromstring(self.filename.encode("ascii"), dtype=np.uint8) | 0x80
        data[3+n:] = ord(' ') | 0x80
        if self.deleted:
            data[0x20] = self.track
        values[4] = self.num_sectors
        return data

    def mark_deleted(self):
        self.deleted = True

    def update_sector_info(self, sector_list):
        self.num_sectors = sector_list.num_sectors
        self.starting_sector = sector_list.first_sector

    def add_metadata_sectors(self, vtoc, sector_list, header):
        """Add track/sector list
        """
        tslist = BaseSectorList(header)
        for start in range(0, len(sector_list), header.ts_pairs):
            end = min(start + header.ts_pairs, len(sector_list))
            if _xd: log.debug("ts: %d-%d" % (start, end))
            s = Dos33TSSector(header, sector_list, start, end)
            s.ts_start, s.ts_end = start, end
            tslist.append(s)
        self.num_tslists = len(tslist)
        vtoc.assign_sector_numbers(self, tslist)
        sector_list.extend(tslist)
        self.track, self.sector = header.track_from_sector(tslist[0].sector_num)
        if _xd: log.debug("track/sector lists:\n%s" % str(tslist))

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
        tslist = BaseSectorList(image.header)
        sector_num = image.header.sector_from_track(self.track, self.sector)
        sector_map = []
        while sector_num > 0:
            image.assert_valid_sector(sector_num)
            if _xd: log.debug("reading track/sector list at %d for %s" % (sector_num, self))
            data, _ = image.get_sectors(sector_num)
            sector = Dos33TSSector(image.header, data=data)
            sector.sector_num = sector_num
            sector_map.extend(sector.get_tslist())
            tslist.append(sector)
            sector_num = sector.next_sector_num
        self.sector_map = sector_map[0:self.num_sectors - len(tslist)]
        self.track_sector_list = tslist
        return tslist

    def get_sectors_in_vtoc(self, image):
        self.get_track_sector_list(image)
        sectors = BaseSectorList(image.header)
        sectors.extend(self.track_sector_list)
        for sector_num in self.sector_map:
            sector = WriteableSector(image.header.sector_size, None, sector_num)
            sectors.append(sector)
        return sectors

    def start_read(self, image):
        if not self.is_sane:
            raise errors.InvalidDirent("Invalid directory entry '%s'" % str(self))
        self.get_track_sector_list(image)
        if _xd: log.debug("start_read: %s, t/s list: %s" % (str(self), str(self.sector_map)))
        self.current_sector_index = 0
        self.current_read = self.num_sectors

    def read_sector(self, image):
        try:
            sector = self.sector_map[self.current_sector_index]
        except IndexError:
            sector = -1  # force ByteNotInFile166 error at next read
        if _xd: log.debug("read_sector: index %d=%d in %s" % (self.current_sector_index,sector, str(self)))
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
        self.filename = '%-30s' % filename[0:30]
        self._file_type = self.text_to_type.get(filetype, 0x04)
        self.locked = False
        self.deleted = False

    def get_binary_start_address(self, image):
        self.start_read(image)
        data, _, _, _ = self.read_sector(image)
        addr = int(data[0]) + 256 * int(data[1])
        return addr


class Dos33Header(BaseHeader):
    file_format = "DOS 3.3"

    def __init__(self):
        BaseHeader.__init__(self, 256)

    def __str__(self):
        return "%s Disk Image (size=%d (%dx%dB)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)

    def check_size(self, size):
        if size != 143360:
            raise errors.InvalidDiskImage("Incorrect size for DOS 3.3 image")
        self.image_size = size
        self.first_vtoc = 17 * 16
        self.num_vtoc = 1
        self.first_directory = self.first_vtoc + 15
        self.num_directory = 8
        self.tracks_per_disk = 35
        self.sectors_per_track = 16
        self.max_sectors = self.tracks_per_disk * self.sectors_per_track


class Dos33DiskImage(DiskImageBase):
    default_executable_extension = "BSAVE"

    def __init__(self, rawdata, filename=""):
        DiskImageBase.__init__(self, rawdata, filename)
        self.default_filetype = "B"

    def __str__(self):
        return str(self.header)

    def read_header(self):
        self.header = Dos33Header()

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
            raise errors.InvalidDiskImage("ProDOS format found; not DOS 3.3 image")
        swap_order = False
        data, style = self.get_sectors(self.header.first_vtoc)
        if data[3] == 3:
            if data[1] < 35 and data[2] < 16:
                data, style = self.get_sectors(self.header.first_vtoc + 14)
                if data[2] != 13:
                    log.warning("DOS 3.3 byte swap needed!")
                    swap_order = True
            else:
                raise errors.InvalidDiskImage("Invalid VTOC location for DOS 3.3")


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
        ('sector_size', 'u2'),
        ])

    def get_vtoc(self):
        data, style = self.get_sectors(self.header.first_vtoc)
        values = data[0:self.vtoc_type.itemsize].view(dtype=self.vtoc_type)[0]
        self.header.first_directory = self.header.sector_from_track(values['cat_track'], values['cat_sector'])
        self.header.sector_size = int(values['sector_size'])
        self.header.max_sectors = int(values['num_tracks']) * int(values['sectors_per_track'])
        self.header.ts_pairs = int(values['max_pairs'])
        self.header.dos_release = values['dos_release']
        self.header.last_track_num = values['last_track']
        self.header.track_alloc_dir = values['track_dir']
        self.assert_valid_sector(self.header.first_directory)

    def get_directory(self, directory=None):
        sector = self.header.first_directory
        num = 0
        files = []
        while sector > 0:
            self.assert_valid_sector(sector)
            if _xd: log.debug("reading catalog sector: %d" % sector)
            values, style = self.get_sectors(sector)
            sector = self.header.sector_from_track(values[1], values[2])
            i = 0xb
            while i < 256:
                dirent = Dos33Dirent(self, num, values[i:i+0x23])
                if dirent.flag == 0:
                    break
                if not dirent.is_sane:
                    log.warning("Illegally formatted directory entry %s" % dirent)
                    self.all_sane = False
                elif not dirent.deleted:
                    files.append(dirent)
                if directory is not None:
                    directory.set(num, dirent)
                if _xd: log.debug("valid directory entry %s" % dirent)
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
        start, count = self.get_contiguous_sectors(self.header.first_vtoc, 1)
        segment = RawTrackSectorSegment(r[start:start+count], self.header.first_vtoc, 1, count, 0, 0, self.header.sector_size, name="VTOC")
        segment.style[:] = get_style_bits(data=True)
        segment.set_comment_at(0x00, "unused")
        segment.set_comment_at(0x01, "Track number of next catalog sector")
        segment.set_comment_at(0x02, "Sector number of next catalog sector")
        segment.set_comment_at(0x03, "Release number of DOS used to format")
        segment.set_comment_at(0x04, "unused")
        segment.set_comment_at(0x06, "Volume number")
        segment.set_comment_at(0x07, "unused")
        segment.set_comment_at(0x27, "Number of track/sector pairs per t/s list sector")
        segment.set_comment_at(0x28, "unused")
        segment.set_comment_at(0x30, "Last track that sectors allocated")
        segment.set_comment_at(0x31, "Track allocation direction")
        segment.set_comment_at(0x32, "unused")
        segment.set_comment_at(0x34, "Tracks per disk")
        segment.set_comment_at(0x35, "Sectors per track")
        segment.set_comment_at(0x36, "Bytes per sector")
        index = 0x38
        for track in range(35):
            segment.set_comment_at(index, "Free sectors in track %d" % track)
            index += 4
        segments.append(segment)
        return segments

    def get_directory_segments(self):
        byte_order = []
        r = self.rawdata
        segments = []
        sector = self.header.first_directory
        while sector > 0:
            self.assert_valid_sector(sector)
            if _xd: log.debug("loading directory segment from catalog sector %d" % sector)
            raw, pos, size = self.get_raw_bytes(sector)
            byte_order.extend(list(range(pos, pos + size)))
            sector = self.header.sector_from_track(raw[1], raw[2])
        raw = self.rawdata.get_indexed(byte_order)
        segment = DefaultSegment(raw, name="Catalog")
        segment.style[:] = get_style_bits(data=True)
        index = 0
        filenum = 0
        while index < len(segment):
            segment.set_comment_at(index + 0x00, "unused")
            segment.set_comment_at(index + 0x01, "Track number of next catalog sector")
            segment.set_comment_at(index + 0x02, "Sector number of next catalog sector")
            segment.set_comment_at(index + 0x03, "unused")
            index += 0x0b
            for i in range(7):
                segment.set_comment_at(index + 0x00, "FILE #%d: Track number of next catalog sector" % filenum)
                segment.set_comment_at(index + 0x01, "FILE #%d: Sector number of next catalog sector" % filenum)
                segment.set_comment_at(index + 0x02, "FILE #%d: File type" % filenum)
                segment.set_comment_at(index + 0x03, "FILE #%d: Filename" % filenum)
                segment.set_comment_at(index + 0x21, "FILE #%d: Number of sectors in file" % filenum)
                index += 0x23
                filenum += 1
        segments.append(segment)
        return segments

    def get_directory_sector_links(self, sector_num):
        if sector_num == -1:
            sector_num = self.header.first_directory
        self.assert_valid_sector(sector_num)
        raw, _, _ = self.get_raw_bytes(sector_num)
        next_sector = self.header.sector_from_track(raw[1], raw[2])
        if _xd: log.debug("checking catalog sector %d, next catalog sector: %d" % (sector_num, next_sector))
        if next_sector == 0:
            raise errors.NoSpaceInDirectory("No space left in catalog")
        return sector_num, next_sector

    def get_file_segment(self, dirent):
        byte_order = []
        dirent.start_read(self)
        while True:
            bytes, last, pos, size = dirent.read_sector(self)
            byte_order.extend(list(range(pos, pos + size)))
            if last:
                break
        if len(byte_order) > 0:
            name = "%s %03d %s" % (dirent.summary, dirent.num_sectors, dirent.filename)
            verbose_name = "%s (%d sectors, first@%d) %s" % (dirent.filename, dirent.num_sectors, dirent.sector_map[0], dirent.verbose_info)
            raw = self.rawdata.get_indexed(byte_order)
            if dirent.file_type == "B":
                addr = dirent.get_binary_start_address(self) - 4 # factor in 4 byte header
            else:
                addr = 0
            segment = ObjSegment(raw, 0, 0, origin=addr, name=name, verbose_name=verbose_name)
            if addr > 0:
                style = segment.get_style_bits(data=True)
                segment.style[0:4] = style
        else:
            segment = EmptySegment(self.rawdata, name=dirent.filename)
        return segment


class Dos33BinFile:
    """Parse a binary chunk into segments according to the DOS 3.3 binary
    dump format
    """

    def __init__(self, rawdata):
        self.rawdata = rawdata
        self.size = len(rawdata)
        self.segments = []
        self.files = []

    def __str__(self):
        return "\n".join(str(s) for s in self.segments) + "\n"

    def strict_check(self):
        pass

    def relaxed_check(self):
        pass

    def parse_segments(self):
        r = self.rawdata
        b = r.get_data()
        s = r.get_style()
        pos = 0
        style_pos = 0
        first = True
        if _xd: log.debug("Initial parsing: size=%d" % self.size)
        if len(b[pos:pos + 4]) == 4:
            start, count = b[pos:pos + 4].view(dtype='<u2')
            if count != self.size - 4:
                raise errors.InvalidBinaryFile(f"Extra data after BSAVE segment: file size {self.size}, header specifies {count} bytes")
            s[pos:pos + 4] = get_style_bits(data=True)
            data = b[pos + 4:pos + 4 + count]
            if len(data) == count:
                name = "BSAVE data" % start
            else:
                raise errors.InvalidBinaryFile(f"Incomplete BSAVE data: expected {count}, loaded {len(data)}")
            self.segments.append(ObjSegment(r[pos + 4:pos + 4 + count], pos, pos + 4, start, start + len(data), name))

        else:
            raise errors.InvalidBinaryFile(f"Invalid BSAVE header")


class ProdosHeader(Dos33Header):
    file_format = "ProDOS"

    def __str__(self):
        return "%s Disk Image (size=%d) THIS FORMAT IS NOT SUPPORTED YET!" % (self.file_format, self.image_size)


class ProdosDiskImage(DiskImageBase):
    def __str__(self):
        return str(self.header)

    def read_header(self):
        self.header = ProdosHeader()

    def get_boot_sector_info(self):
        # based on logic from a2server
        data, style = self.get_sectors(0)
        magic = data[0:4]
        swap_order = False
        if (magic == [1, 56, 176, 3]).all():
            data, style = self.get_sectors(1)
            prodos = data[3:9].tobytes()
            if prodos == "PRODOS":
                pass
            else:
                data, style = self.get_sectors(14)
                prodos = data[3:9].tobytes()
                if prodos == "PRODOS":
                    swap_order = True
                else:
                    # FIXME: this doesn't seem to be the only way to identify a
                    # PRODOS disk. I have example images where PRODOS occurs at
                    # 0x21 - 0x27 in t0s14 and 0x11 - 0x16 in t0s01. Using 3 -
                    # 9 as magic bytes was from the cppo script from
                    # https://github.com/RasppleII/a2server but it seems that
                    # more magic bytes might be acceptable?

                    #raise errors.InvalidDiskImage("No ProDOS header info found")
                    pass
            raise errors.UnsupportedDiskImage("ProDOS format found but not supported")
        raise errors.InvalidDiskImage("Not ProDOS format")
