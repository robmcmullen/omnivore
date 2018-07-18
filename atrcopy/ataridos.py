import numpy as np

from . import errors
from .diskimages import DiskImageBase, BaseHeader
from .segments import SegmentData, EmptySegment, ObjSegment, RawSectorsSegment, DefaultSegment, SegmentedFileSegment, SegmentSaver, get_style_bits
from .utils import *
from .executables import get_xex

import logging
log = logging.getLogger(__name__)
try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class AtariDosWriteableSector(WriteableSector):
    @property
    def next_sector_num(self):
        return self._next_sector_num

    @next_sector_num.setter
    def next_sector_num(self, value):
        self._next_sector_num = value
        index = self.sector_size - 3
        hi, lo = divmod(value, 256)
        self.data[index + 0] = (self.file_num << 2) | (hi & 0x03)
        self.data[index + 1] = lo
        self.data[index + 2] = self.used
        if _xd: log.debug("sector metadata for %d: %s" % (self._sector_num, self.data[index:index + 3]))
        # file number will be added later when known.


class AtariDosVTOC(VTOC):
    def parse_segments(self, segments):
        self.vtoc1 = segments[0].data
        bits = np.unpackbits(self.vtoc1[0x0a:0x64])
        self.sector_map[0:720] = bits
        if _xd: log.debug("vtoc before:\n%s" % str(self))

    def calc_bitmap(self):
        if _xd: log.debug("vtoc after:\n%s" % str(self))
        packed = np.packbits(self.sector_map[0:720])
        self.vtoc1[0x0a:0x64] = packed
        s = WriteableSector(self.sector_size, self.vtoc1)
        s.sector_num = 360
        self.sectors.append(s)


class AtariDosDirectory(Directory):
    @property
    def dirent_class(self):
        return AtariDosDirent

    def encode_empty(self):
        return np.zeros([16], dtype=np.uint8)

    def encode_dirent(self, dirent):
        data = dirent.encode_dirent()
        if _xd: log.debug("encoded dirent: %s" % data)
        return data

    def set_sector_numbers(self, image):
        num = 361
        for sector in self.sectors:
            sector.sector_num = num
            num += 1


class AtariDosDirent(Dirent):
    # ATR Dirent structure described at http://atari.kensclassics.org/dos.htm
    format = np.dtype([
        ('FLAG', 'u1'),
        ('COUNT', '<u2'),
        ('START', '<u2'),
        ('NAME','S8'),
        ('EXT','S3'),
        ])

    def __init__(self, image, file_num=0, bytes=None):
        Dirent.__init__(self, file_num)
        self.flag = 0
        self.opened_output = False
        self.dos_2 = False
        self.mydos = False
        self.is_dir = False
        self.locked = False
        self.in_use = False
        self.deleted = False
        self.num_sectors = 0
        self.starting_sector = 0
        self.basename = b''
        self.ext = b''
        self.is_sane = True
        self.current_sector = 0
        self.current_read = 0
        self.sectors_seen = None
        self.parse_raw_dirent(image, bytes)

    def __str__(self):
        return "File #%-2d (%s) %03d %-8s%-3s  %03d" % (self.file_num, self.summary, self.starting_sector, self.basename.decode("latin1"), self.ext.decode("latin1"), self.num_sectors)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.filename == other.filename and self.starting_sector == other.starting_sector and self.num_sectors == other.num_sectors

    @property
    def filename(self):
        ext = (b'.' + self.ext) if self.ext else b''
        return (self.basename + ext).decode('latin1')

    @property
    def summary(self):
        output = "o" if self.opened_output else "."
        dos2 = "2" if self.dos_2 else "."
        mydos = "m" if self.mydos else "."
        in_use = "u" if self.in_use else "."
        deleted = "d" if self.deleted else "."
        locked = "*" if self.locked else " "
        flags = "%s%s%s%s%s%s" % (output, dos2, mydos, in_use, deleted, locked)
        return flags

    @property
    def verbose_info(self):
        flags = []
        if self.opened_output: flags.append("OUT")
        if self.dos_2: flags.append("DOS2")
        if self.mydos: flags.append("MYDOS")
        if self.in_use: flags.append("IN_USE")
        if self.deleted: flags.append("DEL")
        if self.locked: flags.append("LOCK")
        return "flags=[%s]" % ", ".join(flags)

    def extra_metadata(self, image):
        return self.verbose_info

    def parse_raw_dirent(self, image, data):
        if data is None:
            return
        values = data.view(dtype=self.format)[0]
        flag = values[0]
        self.flag = flag
        self.opened_output = (flag&0x01) > 0
        self.dos_2 = (flag&0x02) > 0
        self.mydos = (flag&0x04) > 0
        self.is_dir = (flag&0x10) > 0
        self.locked = (flag&0x20) > 0
        self.in_use = (flag&0x40) > 0
        self.deleted = (flag&0x80) > 0
        self.num_sectors = int(values[1])
        self.starting_sector = int(values[2])
        self.basename = bytes(values[3]).rstrip()
        self.ext = bytes(values[4]).rstrip()
        self.is_sane = self.sanity_check(image)

    def encode_dirent(self):
        data = np.zeros([self.format.itemsize], dtype=np.uint8)
        values = data.view(dtype=self.format)[0]
        flag = (1 * int(self.opened_output)) | (2 * int(self.dos_2)) | (4 * int(self.mydos)) | (0x10 * int(self.is_dir)) | (0x20 * int(self.locked)) | (0x40 * int(self.in_use)) | (0x80 * int(self.deleted))
        values[0] = flag
        values[1] = self.num_sectors
        values[2] = self.starting_sector
        values[3] = self.basename
        values[4] = self.ext
        return data

    def mark_deleted(self):
        self.deleted = True
        self.in_use = False

    def update_sector_info(self, sector_list):
        self.num_sectors = sector_list.num_sectors
        self.starting_sector = sector_list.first_sector

    def add_metadata_sectors(self, vtoc, sector_list, header):
        # no extra sectors are needed for an Atari DOS file; the links to the
        # next sector is contained in the sector.
        pass

    def sanity_check(self, image):
        if not self.in_use:
            return True
        if not image.header.sector_is_valid(self.starting_sector):
            return False
        if self.num_sectors < 0 or self.num_sectors > image.header.max_sectors:
            return False
        return True

    def get_sectors_in_vtoc(self, image):
        sector_list = BaseSectorList(image.header)
        self.start_read(image)
        while True:
            sector = WriteableSector(image.header.sector_size, None, self.current_sector)
            sector_list.append(sector)
            _, last, _, _ = self.read_sector(image)
            if last:
                break
        return sector_list

    def start_read(self, image):
        if not self.is_sane:
            raise errors.InvalidDirent("Invalid directory entry '%s'" % str(self))
        self.current_sector = self.starting_sector
        self.current_read = self.num_sectors
        self.sectors_seen = set()

    def read_sector(self, image):
        raw, pos, size = image.get_raw_bytes(self.current_sector)
        bytes, num_data_bytes = self.process_raw_sector(image, raw)
        return bytes, self.current_sector == 0, pos, num_data_bytes

    def process_raw_sector(self, image, raw):
        file_num = raw[-3] >> 2
        if file_num != self.file_num:
            raise errors.FileNumberMismatchError164("Expecting file %d, found %d" % (self.file_num, file_num))
        self.sectors_seen.add(self.current_sector)
        next_sector = ((raw[-3] & 0x3) << 8) + raw[-2]
        if next_sector in self.sectors_seen:
            raise errors.InvalidFile("Bad sector pointer data: attempting to reread sector %d" % next_sector)
        self.current_sector = next_sector
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes

    def set_values(self, filename, filetype, index):
        if type(filename) is not bytes:
            filename = filename.encode("latin1")
        if b'.' in filename:
            filename, ext = filename.split(b'.', 1)
        else:
            ext = b'   '
        self.basename = b'%-8s' % filename[0:8]
        self.ext = ext
        self.file_num = index
        self.dos_2 = True
        self.in_use = True
        if _xd: log.debug("set_values: %s" % self)


class MydosDirent(AtariDosDirent):
    def process_raw_sector(self, image, raw):
        # No file number stored in the sector data; two full bytes available
        # for next sector
        self.current_sector = (raw[-3] << 8) + raw[-2]
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes


class XexSegmentSaver(SegmentSaver):
    export_data_name = "Atari 8-bit Executable"
    export_extensions = [".xex"]


class XexContainerSegment(DefaultSegment):
    can_resize_default = True


class XexSegment(ObjSegment):
    savers = [SegmentSaver, XexSegmentSaver]


class RunAddressSegment(ObjSegment):
    # FIXME: defining run_address as a property doesn't work for some reason.
    # @property
    # def run_address(self):
    #     return self.rawdata[0:2].view(dtype="<u2")[0]
    def run_address(self):
        return self.rawdata[0:2].data.view(dtype="<u2")[0]



class AtariDosFile:
    """Parse a binary chunk into segments according to the Atari DOS object
    file format.
    
    Ref: http://www.atarimax.com/jindroush.atari.org/afmtexe.html
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
        while pos < self.size:
            if pos + 1 < self.size:
                header, = b[pos:pos+2].view(dtype='<u2')
            else:
                self.segments.append(ObjSegment(r[pos:pos + 1], pos, pos + 1, 0, 1, "Incomplete Data"))
                break
            if header == 0xffff:
                # Apparently 0xffff header can appear in any segment, not just
                # the first.  Regardless, it is ignored everywhere.
                pos += 2
                first = False
                continue
            elif first:
                raise errors.InvalidBinaryFile("Object file doesn't start with 0xffff")
            if _xd: log.debug("header parsing: header=0x%x" % header)
            if len(b[pos:pos + 4]) < 4:
                self.segments.append(ObjSegment(r[pos:pos + 4], 0, 0, 0, len(b[pos:pos + 4]), "Short Segment Header"))
                break
            start, end = b[pos:pos + 4].view(dtype='<u2')
            s[style_pos:pos + 4] = get_style_bits(data=True)
            if end < start:
                raise errors.InvalidBinaryFile("Nonsensical start and end addresses")
            count = end - start + 1
            found = len(b[pos + 4:pos + 4 + count])
            if found < count:
                self.segments.append(ObjSegment(r[pos + 4:pos + 4 + count], pos, pos + 4, start, end, "Incomplete Data"))
                break
            if start == 0x2e0:
                segment_cls = RunAddressSegment
            else:
                segment_cls = ObjSegment
            print(start, end, segment_cls)
            self.segments.append(segment_cls(r[pos + 4:pos + 4 + count], pos, pos + 4, start, end))
            pos += 4 + count
            style_pos = pos


class AtrHeader(BaseHeader):
    sector_class = AtariDosWriteableSector

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
        BaseHeader.__init__(self, sector_size, initial_sectors, 360, 1)
        if create:
            self.header_offset = 16
            self.check_size(0)
        if bytes is None:
            return

        if len(bytes) == 16:
            values = bytes.view(dtype=self.format)[0]
            if values[0] != 0x296:
                raise errors.InvalidAtrHeader("no ATR header magic value")
            self.image_size = (int(values[3]) * 256 * 256 + int(values[1])) * 16
            self.sector_size = int(values[2])
            self.crc = int(values[4])
            self.unused = int(values[5])
            self.flags = int(values[6])
            self.header_offset = 16
        else:
            raise errors.InvalidAtrHeader("incorrect AHC header size of %d" % len(bytes))

    def __str__(self):
        return "%s Disk Image (size=%d (%dx%dB), crc=%d flags=%d unused=%d)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size, self.crc, self.flags, self.unused)

    def encode(self, raw):
        values = raw.view(dtype=self.format)[0]
        values[0] = 0x296
        paragraphs = self.image_size // 16
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
        self.first_vtoc = 360
        self.num_vtoc = 1
        self.first_directory = 361
        self.num_directory = 8
        self.tracks_per_disk = 40
        self.sectors_per_track = 18
        self.payload_bytes = self.sector_size - 3
        initial_bytes = self.initial_sector_size * self.num_initial_sectors
        self.max_sectors = ((self.image_size - initial_bytes) // self.sector_size) + self.num_initial_sectors

    def get_pos(self, sector):
        if not self.sector_is_valid(sector):
            raise errors.ByteNotInFile166("Sector %d out of range" % sector)
        if sector <= self.num_initial_sectors:
            pos = self.num_initial_sectors * (sector - 1)
            size = self.initial_sector_size
        else:
            pos = self.num_initial_sectors * self.initial_sector_size + (sector - 1 - self.num_initial_sectors) * self.sector_size
            size = self.sector_size
        pos += self.header_offset
        return pos, size

    def strict_check(self, image):
        size = len(image)
        if self.header_offset == 16 or size in [92176, 133136, 184336, 183952]:
            return
        raise errors.InvalidDiskImage("Uncommon size of ATR file")


class XfdHeader(AtrHeader):
    file_format = "XFD"

    def __str__(self):
        return "%s Disk Image (size=%d (%dx%dB)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)

    def __len__(self):
        return 0

    def to_array(self):
        raw = np.zeros([0], dtype=np.uint8)
        return raw

    def strict_check(self, image):
        size = len(image)
        if size in [92160, 133120, 183936, 184320]:
            return
        raise errors.InvalidDiskImage("Uncommon size of XFD file")


class AtariDosDiskImage(DiskImageBase):
    default_executable_extension = "XEX"

    def __init__(self, *args, **kwargs):
        self.first_vtoc = 360
        self.num_vtoc = 1
        self.vtoc2 = 0
        self.first_data_after_vtoc = 369
        DiskImageBase.__init__(self, *args, **kwargs)

    @property
    def writeable_sector_class(self):
        return AtariDosWriteableSector

    @property
    def vtoc_class(self):
        return AtariDosVTOC

    @property
    def directory_class(self):
        return AtariDosDirectory

    def __str__(self):
        return "%s Atari DOS Format: %d usable sectors (%d free), %d files" % (self.header, self.total_sectors, self.unused_sectors, len(self.files))

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

    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    def read_header(self):
        bytes = self.bytes[0:16]
        try:
            self.header = AtrHeader(bytes)
        except errors.InvalidAtrHeader:
            self.header = XfdHeader()

    def calc_vtoc_code(self):
        # From AA post: http://atariage.com/forums/topic/179868-mydos-vtoc-size/
        num = 1 + (self.total_sectors + 80) // (self.header.sector_size * 8)
        if self.header.sector_size == 128:
            if num == 1:
                code = 2
            else:
                if num & 1:
                    num += 1
                code = ((num + 1) // 2) + 2
        else:
            if self.total_sectors < 1024:
                code = 2
            else:
                code = 2 + num
        return code

    def get_vtoc(self):
        data, style = self.get_sectors(360)
        values = data[0:5].view(dtype=self.vtoc_type)[0]
        code = values[0]
        if code == 0 or code == 2:
            num = 1
        else:
            num = (code * 2) - 3
        self.first_vtoc = 360 - num + 1
        self.assert_valid_sector(self.first_vtoc)
        self.num_vtoc = num
        if num < 0 or num > self.calc_vtoc_code():
            raise errors.InvalidDiskImage("Invalid number of VTOC sectors: %d" % num)

        self.total_sectors = values[1]
        self.unused_sectors = values[2]
        if self.header.image_size == 133120:
            # enhanced density has 2nd VTOC
            self.vtoc2 = 1024
            data, style = self.get_sectors(self.vtoc2)
            extra_free = data[122:124].view(dtype='<u2')[0]
            self.unused_sectors += extra_free

    def get_directory(self, directory=None):
        dir_bytes, style = self.get_sectors(361, 368)
        i = 0
        num = 0
        files = []
        while i < len(dir_bytes):
            dirent = AtariDosDirent(self, num, dir_bytes[i:i+16])
            if dirent.mydos:
                dirent = MydosDirent(self, num, dir_bytes[i:i+16])

            if dirent.in_use:
                files.append(dirent)
                if not dirent.is_sane:
                    self.all_sane = False
                    log.debug("dirent %d not sane: %s" % (num, dirent))
            elif dirent.flag == 0:
                break
            if directory is not None:
                directory.set(num, dirent)
            i += 16
            num += 1
        self.files = files

    boot_record_type = np.dtype([
        ('BFLAG', 'u1'),
        ('BRCNT', 'u1'),
        ('BLDADR', '<u2'),
        ('BWTARR', '<u2'),
        ('jmp', 'u1'),
        ('XBCONT', '<u2'),
        ('SABYTE', 'u1'),
        ('DRVBYT', 'u1'),
        ('unused', 'u1'),
        ('SASA', '<u2'),
        ('DFSFLG', 'u1'),
        ('DFLINK', '<u2'),
        ('BLDISP', 'u1'),
        ('DFLADR', '<u2'),
        ])

    def get_boot_segments(self):
        data, style = self.get_sectors(360)
        values = data[0:20].view(dtype=self.boot_record_type)[0]
        flag = int(values[0])
        segments = []
        if flag == 0:
            num = int(values[1])
            addr = int(values[2])
            s = self.get_sector_slice(1, num)
            r = self.rawdata[s]
            header = ObjSegment(r[0:20], 0, 0, addr, addr + 20, name="Boot Header")
            sectors = ObjSegment(r, 0, 0, addr, addr + len(r), name="Boot Sectors")
            code = ObjSegment(r[20:], 0, 0, addr + 20, addr + len(r), name="Boot Code")
            segments = [sectors, header, code]
        return segments

    def get_vtoc_segments(self):
        r = self.rawdata
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(self.first_vtoc, self.num_vtoc)
        segment = RawSectorsSegment(r[start:start+count], self.first_vtoc, self.num_vtoc, count, 128, 3, self.header.sector_size, name="VTOC")
        segment.style[:] = get_style_bits(data=True)
        segment.set_comment_at(0x00, "Type code")
        segment.set_comment_at(0x01, "Total number of sectors")
        segment.set_comment_at(0x03, "Number of free sectors")
        segment.set_comment_at(0x05, "reserved")
        segment.set_comment_at(0x06, "unused")
        segment.set_comment_at(0x0a, "Sector bit map")
        segment.set_comment_at(0x64, "unused")
        segments.append(segment)
        if self.vtoc2 > 0:
            start, count = self.get_contiguous_sectors(self.vtoc2, 1)
            segment = RawSectorsSegment(r[start:start+count], self.vtoc2, 1, count, 128, 3, self.header.sector_size, name="VTOC2")
            segment.style[:] = get_style_bits(data=True)
            segment.set_comment_at(0x00, "Repeat of sectors 48-719")
            segment.set_comment_at(0x44, "Sector bit map 720-1023")
            segment.set_comment_at(0x7a, "Number of free sectors above 720")
            segment.set_comment_at(0x7c, "unused")
            segments.append(segment)
        return segments

    def get_directory_segments(self):
        r = self.rawdata
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(361, 8)
        segment = RawSectorsSegment(r[start:start+count], 361, 8, count, 128, 3, self.header.sector_size, name="Directory")
        segment.style[:] = get_style_bits(data=True)
        index = 0
        for filenum in range(64):
            segment.set_comment_at(index + 0x00, "FILE #%d: Flag" % filenum)
            segment.set_comment_at(index + 0x01, "FILE #%d: Number of sectors in file" % filenum)
            segment.set_comment_at(index + 0x03, "FILE #%d: Starting sector number" % filenum)
            segment.set_comment_at(index + 0x05, "FILE #%d: Filename" % filenum)
            segment.set_comment_at(index + 0x0d, "FILE #%d: Extension" % filenum)
            index += 16
        segments.append(segment)
        return segments

    def get_file_segment(self, dirent):
        byte_order = []
        dirent.start_read(self)
        while True:
            bytes, last, pos, size = dirent.read_sector(self)
            byte_order.extend(list(range(pos, pos + size)))
            if last:
                break
        if len(byte_order) > 0:
            name = "%s %ds@%d" % (dirent.filename, dirent.num_sectors, dirent.starting_sector)
            verbose_name = "%s (%d sectors, first@%d) %s" % (dirent.filename, dirent.num_sectors, dirent.starting_sector, dirent.verbose_info)
            raw = self.rawdata.get_indexed(byte_order)
            segment = DefaultSegment(raw, name=name, verbose_name=verbose_name)
        else:
            segment = EmptySegment(self.rawdata, name=dirent.filename)
        return segment

    def get_file_segments(self):
        segments_in = DiskImageBase.get_file_segments(self)
        segments_out = []
        for segment in segments_in:
            segments_out.append(segment)
            try:
                binary = AtariDosFile(segment.rawdata)
                segments_out.extend(binary.segments)
            except errors.InvalidBinaryFile:
                log.debug("%s not a binary file; skipping segment generation" % str(segment))
        return segments_out


class BootDiskImage(AtariDosDiskImage):
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
            raise errors.InvalidDiskImage("Appears to be an executable")
        nsec = b[i + 1]
        bload = b[i + 2:i + 4].view(dtype='<u2')[0]

        # Sanity check: number of sectors to be loaded can't be more than the
        # lower 48k of ram because there's no way to bank switch or anything
        # before the boot sectors are finished loading
        max_ram = 0xc000
        max_size = max_ram - bload
        max_sectors = max_size // self.header.sector_size
        if nsec > max_sectors or nsec < 1:
            raise errors.InvalidDiskImage("Number of boot sectors out of range (tried %d, max=%d" % (nsec, max_sectors))
        if bload > (0xc000 - (nsec * self.header.sector_size)):
            raise errors.InvalidDiskImage("Bad boot load address")

    def get_boot_sector_info(self):
        pass

    def get_vtoc(self):
        pass

    def get_directory(self, directory=None):
        pass

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


class AtariDiskImage(BootDiskImage):
    def __str__(self):
        return "%s Unidentified Contents" % (self.header)

    def check_size(self):
        if self.header is None:
            raise errors.InvalidDiskImage("Not a known Atari disk image format")

    def get_boot_segments(self):
        return []


def add_atr_header(bytes):
    header = AtrHeader(create=True)
    header.check_size(len(bytes))
    hlen = len(header)
    data = np.empty([hlen + len(bytes)], dtype=np.uint8)
    data[0:hlen] = header.to_array()
    data[hlen:] = bytes
    return data
