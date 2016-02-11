#!/usr/bin/env python


__version__ = "2.1.1"

import types

try:
    import numpy as np
except ImportError:
    raise RuntimeError("atrcopy %s requires numpy" % __version__)


class AtrError(RuntimeError):
    pass

class InvalidAtrHeader(AtrError):
    pass

class InvalidDiskImage(AtrError):
    pass

class InvalidDirent(AtrError):
    pass

class LastDirent(AtrError):
    pass

class InvalidFile(AtrError):
    pass

class FileNumberMismatchError164(InvalidFile):
    pass

class ByteNotInFile166(InvalidFile):
    pass

class InvalidBinaryFile(InvalidFile):
    pass


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
    
    def __init__(self, bytes=None):
        self.image_size = 0
        self.sector_size = 0
        self.crc = 0
        self.unused = 0
        self.flags = 0
        self.atr_header_offset = 0
        self.initial_sector_size = 0
        self.num_initial_sectors = 0
        self.max_sectors = 0
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
            self.atr_header_offset = 16
        else:
            raise InvalidAtrHeader
    
    def __str__(self):
        return "%s Disk Image (size=%d (%dx%db), crc=%d flags=%d unused=%d)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size, self.crc, self.flags, self.unused)

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
            self.sector_size = 128
        initial_bytes = self.initial_sector_size * self.num_initial_sectors
        self.max_sectors = ((self.image_size - initial_bytes) / self.sector_size) + self.num_initial_sectors
    
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
        pos += self.atr_header_offset
        return pos, size

class XfdHeader(AtrHeader):
    file_format = "XFD"
    
    def __str__(self):
        return "%s Disk Image (size=%d (%dx%db)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)

class AtrDirent(object):
    # ATR Dirent structure described at http://atari.kensclassics.org/dos.htm
    format = np.dtype([
        ('FLAG', 'u1'),
        ('COUNT', '<u2'),
        ('START', '<u2'),
        ('NAME','S8'),
        ('EXT','S3'),
        ])

    def __init__(self, disk, file_num=0, bytes=None):
        self.file_num = file_num
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
        self.filename = ""
        self.ext = ""
        self.is_sane = True
        self.current_sector = 0
        self.current_read = 0
        self.sectors_seen = None
        if bytes is None:
            return
        values = bytes.view(dtype=self.format)[0]  
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
        self.filename = str(values[3]).rstrip()
        self.ext = str(values[4]).rstrip()
        self.is_sane = self.sanity_check(disk)
    
    def __str__(self):
        output = "o" if self.opened_output else "."
        dos2 = "2" if self.dos_2 else "."
        mydos = "m" if self.mydos else "."
        in_use = "u" if self.in_use else "."
        deleted = "d" if self.deleted else "."
        locked = "*" if self.locked else " "
        flags = "%s%s%s%s%s%s %03d" % (output, dos2, mydos, in_use, deleted, locked, self.starting_sector)
        if self.in_use:
            return "File #%-2d (%s) %-8s%-3s  %03d" % (self.file_num, flags, self.filename, self.ext, self.num_sectors)
        return
    
    def sanity_check(self, disk):
        if not self.in_use:
            return True
        if not disk.header.sector_is_valid(self.starting_sector):
            return False
        if self.num_sectors < 0 or self.num_sectors > disk.header.max_sectors:
            return False
        return True
    
    def start_read(self):
        if not self.is_sane:
            raise InvalidDirent("Invalid directory entry '%s'" % str(self))
        self.current_sector = self.starting_sector
        self.current_read = self.num_sectors
        self.sectors_seen = set()
    
    def read_sector(self, disk):
        raw, pos, size = disk.get_raw_bytes(self.current_sector)
        bytes, num_data_bytes = self.process_raw_sector(disk, raw)
        return bytes, self.current_sector == 0, pos, num_data_bytes

    def process_raw_sector(self, disk, raw):
        file_num = raw[-3] >> 2
        if file_num != self.file_num:
            raise FileNumberMismatchError164()
        self.sectors_seen.add(self.current_sector)
        next_sector = ((raw[-3] & 0x3) << 8) + raw[-2]
        if next_sector in self.sectors_seen:
            raise InvalidFile("Bad sector pointer data: attempting to reread sector %d" % next_sector)
        self.current_sector = next_sector
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes
    
    def get_filename(self):
        ext = ("." + self.ext) if self.ext else ""
        return self.filename + ext

class MydosDirent(AtrDirent):
    def process_raw_sector(self, disk, raw):
        # No file number stored in the sector data; two full bytes available
        # for next sector
        self.current_sector = (raw[-3] << 8) + raw[-2]
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes


class SegmentSaver(object):
    name = "Raw Data"
    extensions = [".dat"]
    
    @classmethod
    def encode_data(cls, segment):
        return segment.tostring()

    @classmethod
    def get_file_dialog_wildcard(cls):
        # Using only the first extension
        wildcards = []
        if cls.extensions:
            ext = cls.extensions[0]
            wildcards.append("%s (*%s)|*%s" % (cls.name, ext, ext))
        return "|".join(wildcards)

class XEXSegmentSaver(SegmentSaver):
    name = "Atari 8-bit Executable"
    extensions = [".xex"]


class DefaultSegment(object):
    savers = [SegmentSaver]
    
    def __init__(self, data, style, start_addr=0, name="All", error=None):
        self.start_addr = int(start_addr)  # force python int to decouple from possibly being a numpy datatype
        self.data = data
        self.style = style
        self.error = error
        self.name = name
        self.page_size = -1
        self.map_width = 40
        self._search_copy = None
    
    def __str__(self):
        return "%s (%d bytes)" % (self.name, len(self))
    
    def __len__(self):
        return np.alen(self.data)
    
    def __getitem__(self, index):
        return self.data[index]
    
    def __setitem__(self, index, value):
        self.data[index] = value
        self._search_copy = None
    
    def byte_bounds_offset(self):
        return np.byte_bounds(self.data)[0]

    def tostring(self):
        return self.data.tostring()
    
    def get_style_bits(self, match=False, comment=False, selected=False):
        style_bits = 0
        if match:
            style_bits |= 1
        if comment:
            style_bits |= 2
        if selected:
            style_bits |= 0x80
        return style_bits
    
    def get_style_mask(self, **kwargs):
        return 0xff ^ self.get_style_bits(**kwargs)
    
    def set_style_ranges(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            if end < start:
                start, end = end, start
            s[start:end] |= style_bits
    
    def get_rect_indexes(self, anchor_start, anchor_end):
        # determine row,col of upper left and lower right of selected
        # rectangle.  The values are inclusive, so ul=(0,0) and lr=(1,2)
        # is 2 rows and 3 columns.  Columns need to be adjusted slightly
        # depending on quadrant of selection because anchor indexes are
        # measured as cursor positions, that is: positions between the
        # bytes where as rect select needs to think of the selections as
        # on the byte positions themselves, not in between.
        bpr = self.map_width
        r1, c1 = divmod(anchor_start, bpr)
        r2, c2 = divmod(anchor_end, bpr)
        if c1 >= c2:
            # start column is to the right of the end column so columns
            # need to be swapped
            if r1 >= r2:
                # start row is below end row, so rows swapped as well
                c1, c2 = c2, c1 + 1
                r1, r2 = r2, r1
            elif c2 == 0:
                # When the cursor is at the end of a line, anchor_end points
                # to the first character of the next line.  Handle this
                # special case by pointing to end of the previous line.
                c2 = bpr
                r2 -= 1
            else:
                c1, c2 = c2 - 1, c1 + 1
        else:
            # start column is to the left of the end column, so don't need
            # to swap columns
            if r1 > r2:
                # start row is below end row
                r1, r2 = r2, r1
                c2 += 1
        anchor_start = r1 * bpr + c1
        anchor_end = r2 * bpr + c2
        r2 += 1
        return anchor_start, anchor_end, (r1, c1), (r2, c2)
    
    def set_style_ranges_rect(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            start, end, (r1, c1), (r2, c2) = self.get_rect_indexes(start, end)
            # Numpy tricks!
            # >>> c1 = 15
            # >>> r = 4 # r2 - r1
            # >>> c = 10 # c2 - c1
            # >>> width = 40
            # >>> np.arange(c)
            #array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
            # >>> np.arange(r) * width
            #array([  0,  40,  80, 120])
            # >>> np.tile(np.arange(c), r) + np.repeat(np.arange(r)*width, c)
            #array([  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  40,  41,  42,
            #        43,  44,  45,  46,  47,  48,  49,  80,  81,  82,  83,  84,  85,
            #        86,  87,  88,  89, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129])
            # >>> np.tile(np.arange(c), r) + np.repeat(np.arange(r)*width, c) + c1
            #array([ 15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  55,  56,  57,
            #        58,  59,  60,  61,  62,  63,  64,  95,  96,  97,  98,  99, 100,
            #       101, 102, 103, 104, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144])
            r = r2 - r1
            c = c2 - c1
            indexes = np.tile(np.arange(c), r) + np.repeat(np.arange(r) * self.map_width, c) + start
            s[indexes] |= style_bits
    
    def rects_to_ranges(self, rects):
        ranges = []
        bpr = self.map_width
        for (r1, c1), (r2, c2) in rects:
            start = r1 * bpr + c1
            end = (r2 - 1) * bpr + c2
            ranges.append((start, end))
        return ranges
    
    def clear_style_bits(self, **kwargs):
        style_mask = self.get_style_mask(**kwargs)
        self.style &= style_mask
    
    def label(self, index, lower_case=True):
        if lower_case:
            return "%04x" % (index + self.start_addr)
        else:
            return "%04X" % (index + self.start_addr)
    
    @property
    def search_copy(self):
        if self._search_copy is None:
            self._search_copy = self.data.tostring()
        return self._search_copy

class EmptySegment(DefaultSegment):
    def __init__(self, data, style, name="", error=None):
        DefaultSegment.__init__(self, data, style, 0, name, error)
    
    def __str__(self):
        return "%s (empty file)" % (self.name, )
    
    def __len__(self):
        return 0

class ObjSegment(DefaultSegment):
    def __init__(self, data, style, metadata_start, data_start, start_addr, end_addr,  name="", error=None):
        DefaultSegment.__init__(self, data, style, start_addr, name, error)
        self.metadata_start = metadata_start
        self.data_start = data_start
    
    def __str__(self):
        count = len(self)
        s = "%s $%04x-$%04x ($%04x @ $%04x)" % (self.name, self.start_addr, self.start_addr + count, count, self.data_start)
        if self.error:
            s += " " + self.error
        return s

class XexSegment(ObjSegment):
    savers = [SegmentSaver, XEXSegmentSaver]

class RawSectorsSegment(DefaultSegment):
    def __init__(self, data, style, first_sector, num_sectors, count, **kwargs):
        DefaultSegment.__init__(self, data, style, 0, **kwargs)
        self.page_size = 128
        self.first_sector = first_sector
        self.num_sectors = num_sectors
    
    def __str__(self):
        if self.num_sectors > 1:
            s = "%s (sectors %d-%d)" % (self.name, self.first_sector, self.first_sector + self.num_sectors - 1)
        else:
            s = "%s (sector %d)" % (self.name, self.first_sector)
        if self.error:
            s += " " + self.error
        return s
    
    def label(self, index, lower_case=True):
        sector, byte = divmod(index, self.page_size)
        if lower_case:
            return "s%03d:%02x" % (sector + self.first_sector, byte)
        return "s%03d:%02X" % (sector + self.first_sector, byte)

class IndexedByteSegment(DefaultSegment):
    def __init__(self, data, style, byte_order, **kwargs):
        self.order = byte_order
        DefaultSegment.__init__(self, data, style, 0, **kwargs)
    
    def __str__(self):
        return "%s ($%x @ $%x)" % (self.name, len(self), self.order[0])
    
    def __len__(self):
        return np.alen(self.order)
    
    def __getitem__(self, index):
        return self.data[self.order[index]]
    
    def __setitem__(self, index, value):
        self.data[self.order[index]] = value
        self._search_copy = None
    
    def byte_bounds_offset(self):
        return np.byte_bounds(self.data)[0] + self.order[0]
    
    def tostring(self):
        return self.data[self.order[:]].tostring()


class AtariDosFile(object):
    """Parse a binary chunk into segments according to the Atari DOS object
    file format.
    
    Ref: http://www.atarimax.com/jindroush.atari.org/afmtexe.html
    """
    def __init__(self, data, style=None):
        self.bytes = to_numpy(data)
        self.size = np.alen(self.bytes)
        if style is None:
            self.style = np.zeros(self.size, dtype=np.uint8)
        else:
            self.style = style
        self.segments = []
        self.parse_segments()
    
    def __str__(self):
        return "\n".join(str(s) for s in self.segments) + "\n"
    
    def parse_segments(self):
        b = self.bytes
        s = self.style
        pos = 0
        first = True
        while pos < self.size:
            if pos + 1 < self.size:
                header, = b[pos:pos+2].view(dtype='<u2')
            else:
                self.segments.append(ObjSegment(b[pos:pos + 1], s[pos:pos + 1], pos, pos + 1, 0, 1, "Incomplete Data"))
                break
            if header == 0xffff:
                # Apparently 0xffff header can appear in any segment, not just
                # the first.  Regardless, it is ignored everywhere.
                pos += 2
            elif first:
                raise InvalidBinaryFile
            first = False
            if len(b[pos:pos + 4]) < 4:
                self.segments.append(ObjSegment(b[pos:pos + 4], s[pos:pos + 4], 0, 0, "Short Segment Header"))
                break
            start, end = b[pos:pos + 4].view(dtype='<u2')
            count = end - start + 1
            found = len(b[pos + 4:pos + 4 + count])
            if found < count:
                self.segments.append(ObjSegment(b[pos + 4:pos + 4 + count], s[pos + 4:pos + 4 + count], pos, pos + 4, start, end, "Incomplete Data"))
                break
            self.segments.append(ObjSegment(b[pos + 4:pos + 4 + count], s[pos + 4:pos + 4 + count], pos, pos + 4, start, end))
            pos += 4 + count


class DiskImageBase(object):
    debug = False

    def __init__(self, bytes, style=None, filename=""):
        self.bytes = to_numpy(bytes)
        self.size = np.alen(self.bytes)
        if style is None:
            if self.debug:
                self.style = np.arange(self.size, dtype=np.uint8)
            else:
                self.style = np.zeros(self.size, dtype=np.uint8)
        else:
            self.style = style
        self.set_filename(filename)
        self.header = None
        self.total_sectors = 0
        self.unused_sectors = 0
        self.files = []
        self.segments = []
        self.all_sane = True
        self.setup()
    
    def set_filename(self, filename):
        if "." in filename:
            self.filename, self.ext = filename.rsplit(".", 1)
        else:
            self.filename, self.ext = filename, ""

    def setup(self):
        self.size = np.alen(self.bytes)
        self.read_atr_header()
        self.check_size()
        self.get_vtoc()
        self.get_directory()
        self.check_sane()
    
    def check_sane(self):
        if not self.all_sane:
            raise InvalidDiskImage("Invalid directory entries; may be boot disk")
    
    def read_atr_header(self):
        bytes = self.bytes[0:16]
        try:
            self.header = AtrHeader(bytes)
        except InvalidAtrHeader:
            self.header = XfdHeader()
    
    def check_size(self):
        self.header.check_size(self.size)
    
    def get_vtoc(self):
        pass
    
    def get_directory(self):
        pass
    
    def get_raw_bytes(self, sector):
        pos, size = self.header.get_pos(sector)
        return self.bytes[pos:pos + size], pos, size
    
    def get_sectors(self, start, end=None):
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
        return self.bytes[pos:pos + size], self.style[pos:pos + size]
    
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
        b = self.bytes
        s = self.style
        i = self.header.atr_header_offset
        if self.header.image_size > 0:
            self.segments.append(ObjSegment(b[0:i], s[0:i], 0, 0, 0, i, name="%s Header" % self.header.file_format))
        self.segments.append(RawSectorsSegment(b[i:], s[i:], 1, self.header.max_sectors, self.header.image_size, name="Raw disk sectors"))
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
                segment = EmptySegment(self.data, style, name=dirent.get_filename(), error=str(e))
            segments.append(segment)
        return segments


class BootDiskImage(DiskImageBase):
    def __str__(self):
        return "%s Boot Disk" % (self.header)
    
    def check_size(self):
        self.header.check_size(self.size)
        
        start, size = self.header.get_pos(1)
        b = self.bytes
        i = self.header.atr_header_offset
        flag = b[i:i + 2].view(dtype='<u2')[0]
        if flag == 0xffff:
            raise InvalidDiskImage("Appears to be an executable")
        nsec = b[i + 1]
        bload = b[i + 2:i + 4].view(dtype='<u2')[0]
        binit = b[i + 4:i + 6].view(dtype='<u2')[0]
        blen, _ = self.header.get_pos(nsec + 1)
        print nsec, bload, binit, blen
        if not (bload < binit < bload + blen):
            raise InvalidDiskImage("Incorrect boot load/init parameters")


class AtariDosDiskImage(DiskImageBase):
    def __init__(self, bytes, style=None):
        self.first_vtoc = 360
        self.num_vtoc = 1
        self.vtoc2 = 0
        self.first_data_after_vtoc = 369
        DiskImageBase.__init__(self, bytes, style)
    
    def __str__(self):
        if self.all_sane:
            return "%s Atari DOS Format: %d usable sectors (%d free), %d files" % (self.header, self.total_sectors, self.unused_sectors, len(self.files))
        else:
            return "%s bad directory entries; possible boot disk? Use -f option to try to extract anyway" % self.header
    
    def dir(self):
        lines = []
        lines.append(str(self))
        for dirent in self.files:
            if dirent.in_use:
                lines.append(str(dirent))
        return "\n".join(lines)
    
    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    def get_vtoc(self):
        data, style = self.get_sectors(360)
        values = data[0:5].view(dtype=self.vtoc_type)[0]
        code = values[0]
        if code == 0 or code == 2:
            num = 1
        else:
            num = (code * 2) - 3
        self.first_vtoc = 360 - num + 1
        self.num_vtoc = num
        self.total_sectors = values[1]
        self.unused_sectors = values[2]
        if self.header.image_size == 133120:
            # enhanced density has 2nd VTOC
            self.vtoc2 = 1024
            extra_free = self.get_sectors(self.vtoc2)[122:124].view(dtype='<u2')[0]
            self.unused_sectors += extra_free
    
    def get_directory(self):
        dir_bytes, style = self.get_sectors(361, 368)
        i = 0
        num = 0
        files = []
        while i < len(dir_bytes):
            dirent = AtrDirent(self, num, dir_bytes[i:i+16])
            if dirent.mydos:
                dirent = MydosDirent(self, num, dir_bytes[i:i+16])
            
            if dirent.in_use:
                files.append(dirent)
                if not dirent.is_sane:
                    self.all_sane = False
            elif dirent.flag == 0:
                break
            i += 16
            num += 1
        self.files = files
    
    def find_file(self, filename):
        for dirent in self.files:
            if filename == dirent.get_filename():
                return self.get_file(dirent)
        return ""
    
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
            bytes, style = self.get_sectors(1, num)
            header = ObjSegment(bytes[0:20], style[0:20], 0, 0, addr, addr + 20, name="Boot Header")
            sectors = ObjSegment(bytes, style, 0, 0, addr, addr + len(bytes), name="Boot Sectors")
            code = ObjSegment(bytes[20:], style[20:], 0, 0, addr + 20, addr + len(bytes), name="Boot Code")
            segments = [sectors, header, code]
        return segments
    
    def get_vtoc_segments(self):
        b = self.bytes
        s = self.style
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(self.first_vtoc, self.num_vtoc)
        segment = RawSectorsSegment(b[start:start+count], s[start:start+count], self.first_vtoc, self.num_vtoc, count, name="VTOC")
        segments.append(segment)
        if self.vtoc2 > 0:
            start, count = self.get_contiguous_sectors(self.vtoc2, 1)
            segment = RawSectorsSegment(b[start:start+count], s[start:start+count], self.vtoc2, 1, count, name="VTOC2")
            segments.append(segment)
        return segments
    
    def get_directory_segments(self):
        b = self.bytes
        s = self.style
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(361, 8)
        segment = RawSectorsSegment(b[start:start+count], s[start:start+count], 361, 8, count, name="Directory")
        segments.append(segment)
        return segments
    
    def get_file_segment(self, dirent):
        byte_order = []
        dirent.start_read()
        while True:
            bytes, last, pos, size = dirent.read_sector(self)
            byte_order.extend(range(pos, pos + size))
            if last:
                break
        if len(byte_order) > 0:
            segment = IndexedByteSegment(self.bytes, self.style, byte_order, name=dirent.get_filename())
        else:
            segment = EmptySegment(self.bytes, self.style, name=dirent.get_filename())
        return segment


class KBootDirent(AtrDirent):
    def __init__(self, image):
        AtrDirent.__init__(self, image)
        self.in_use = True
        self.starting_sector = 4
        self.filename = image.filename
        if not self.filename:
            self.filename = "KBOOT"
        if self.filename == self.filename.upper():
            self.ext = "XEX"
        else:
            self.ext = "xex"
        start, size = image.header.get_pos(4)
        i = image.header.atr_header_offset + 9
        count = image.bytes[i] + 256 * image.bytes[i+1] + 256 * 256 *image.bytes[i + 2]
        if start + count > image.size or start + count < image.size - 128:
            self.is_sane = False
        else:
            self.exe_size = count
            self.exe_start = start
        self.num_sectors = count / 128 + 1

    def process_raw_sector(self, disk, raw):
        num_bytes = np.alen(raw)
        return raw[0:num_bytes], num_bytes


class KBootImage(DiskImageBase):
    def __str__(self):
        return "%s KBoot Format: %d byte executable" % (self.header, self.files[0].exe_size)
    
    def check_size(self):
        self.header.check_size(self.size)
    
    def check_sane(self):
        if not self.all_sane:
            raise InvalidDiskImage("Doesn't seem to be KBoot header")
    
    def get_directory(self):
        dirent = KBootDirent(self)
        if not dirent.is_sane:
            self.all_sane = False
        self.files = [dirent]

    def get_file_segment(self, dirent):
        start = dirent.exe_start
        end = dirent.exe_start + dirent.exe_size
        return XexSegment(self.bytes[start:end], self.style[start:end], 0, 0, 0, start, name="KBoot Executable")


def to_numpy(value):
    if type(value) is np.ndarray:
        return value
    elif type(value) is types.StringType:
        return np.fromstring(value, dtype=np.uint8)
    raise TypeError("Can't convert to numpy data")

def process(image, dirent, options):
    skip = False
    action = "copying to"
    filename = dirent.get_filename()
    outfilename = filename
    if options.no_sys:
        if dirent.ext == "SYS":
            skip = True
            action = "skipping system file"
    if not skip:
        if options.xex:
            outfilename = "%s%s.XEX" % (dirent.filename, dirent.ext)
    if options.lower:
        outfilename = outfilename.lower()
    
    if options.dry_run:
        action = "DRY_RUN: %s" % action
        skip = True
    if options.extract:
        print "%s: %s %s" % (dirent, action, outfilename)
        if not skip:
            bytes = image.get_file(dirent)
            with open(outfilename, "wb") as fh:
                fh.write(bytes)
    else:
        print dirent

def run():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract images off ATR format disks")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("-l", "--lower", action="store_true", default=False, help="convert filenames to lower case")
    parser.add_argument("--dry-run", action="store_true", default=False, help="don't extract, just show what would have been extracted")
    parser.add_argument("-n", "--no-sys", action="store_true", default=False, help="only extract things that look like games (no DOS or .SYS files)")
    parser.add_argument("-x", "--extract", action="store_true", default=False, help="extract files")
    parser.add_argument("--xex", action="store_true", default=False, help="add .xex extension")
    parser.add_argument("-f", "--force", action="store_true", default=False, help="force operation on disk images that have bad directory entries or look like boot disks")
    parser.add_argument("files", metavar="ATR", nargs="+", help="an ATR image file [or a list of them]")
    parser.add_argument("-s", "--segments", action="store_true", default=False, help="display segments")
    options, extra_args = parser.parse_known_args()

    for filename in options.files:
        with open(filename, "rb") as fh:
            data = fh.read()
            image = None
            try:
                data = to_numpy(data)
                try:
                    header = AtrHeader(data[0:16])
                    for format in [KBootImage, AtariDosDiskImage]:
                        if options.verbose: print "trying", format.__name__
                        try:
                            image = format(data, filename)
                            print "%s: %s" % (filename, image)
                            break
                        except InvalidDiskImage:
                            pass
                except AtrError:
                    for format in [AtariDosDiskImage]:
                        try:
                            image = format(data)
                            print "%s: %s" % (filename, image)
                            break
                        except:
                            raise
                            #pass
            except AtrError:
                if options.verbose: print "%s: Doesn't look like a supported disk image" % filename
                try:
                    image = AtariDosFile(data)
                    print "%s:\n%s" % (filename, image)
                except InvalidBinaryFile:
                    if options.verbose: print "%s: Doesn't look like an XEX either" % filename
                continue
            if image is None:
                image = BootDiskImage(data, filename)
            if options.segments:
                image.parse_segments()
                print "\n".join([str(a) for a in image.segments])
            elif image.files or options.force:
                for dirent in image.files:
                    try:
                        process(image, dirent, options)
                    except FileNumberMismatchError164:
                        print "Error 164: %s" % str(dirent)
                    except ByteNotInFile166:
                        print "Invalid sector for: %s" % str(dirent)

if __name__ == "__main__":
    run()
