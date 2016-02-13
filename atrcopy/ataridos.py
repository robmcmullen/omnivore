import numpy as np

from errors import *
from diskimages import DiskImageBase
from segments import EmptySegment, ObjSegment, RawSectorsSegment, IndexedByteSegment, SegmentSaver
from utils import to_numpy


class AtariDosDirent(object):
    # ATR Dirent structure described at http://atari.kensclassics.org/dos.htm
    format = np.dtype([
        ('FLAG', 'u1'),
        ('COUNT', '<u2'),
        ('START', '<u2'),
        ('NAME','S8'),
        ('EXT','S3'),
        ])

    def __init__(self, image, file_num=0, bytes=None):
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
        self.parse_raw_dirent(image, bytes)
    
    def __str__(self):
        output = "o" if self.opened_output else "."
        dos2 = "2" if self.dos_2 else "."
        mydos = "m" if self.mydos else "."
        in_use = "u" if self.in_use else "."
        deleted = "d" if self.deleted else "."
        locked = "*" if self.locked else " "
        flags = "%s%s%s%s%s%s %03d" % (output, dos2, mydos, in_use, deleted, locked, self.starting_sector)
        return "File #%-2d (%s) %-8s%-3s  %03d" % (self.file_num, flags, self.filename, self.ext, self.num_sectors)
    
    def parse_raw_dirent(self, image, bytes):
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
        self.is_sane = self.sanity_check(image)
    
    def sanity_check(self, image):
        if not self.in_use:
            return True
        if not image.header.sector_is_valid(self.starting_sector):
            return False
        if self.num_sectors < 0 or self.num_sectors > image.header.max_sectors:
            return False
        return True
    
    def start_read(self, image):
        if not self.is_sane:
            raise InvalidDirent("Invalid directory entry '%s'" % str(self))
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


class MydosDirent(AtariDosDirent):
    def process_raw_sector(self, image, raw):
        # No file number stored in the sector data; two full bytes available
        # for next sector
        self.current_sector = (raw[-3] << 8) + raw[-2]
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes


class XexSegmentSaver(SegmentSaver):
    name = "Atari 8-bit Executable"
    extensions = [".xex"]


class XexSegment(ObjSegment):
    savers = [SegmentSaver, XexSegmentSaver]


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


class AtariDosDiskImage(DiskImageBase):
    def __init__(self, bytes, style=None):
        self.first_vtoc = 360
        self.num_vtoc = 1
        self.vtoc2 = 0
        self.first_data_after_vtoc = 369
        DiskImageBase.__init__(self, bytes, style)
    
    def __str__(self):
        return "%s Atari DOS Format: %d usable sectors (%d free), %d files" % (self.header, self.total_sectors, self.unused_sectors, len(self.files))
    
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
            dirent = AtariDosDirent(self, num, dir_bytes[i:i+16])
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
        segment = RawSectorsSegment(b[start:start+count], s[start:start+count], self.first_vtoc, self.num_vtoc, count, 128, 3, self.header.sector_size, name="VTOC")
        segments.append(segment)
        if self.vtoc2 > 0:
            start, count = self.get_contiguous_sectors(self.vtoc2, 1)
            segment = RawSectorsSegment(b[start:start+count], s[start:start+count], self.vtoc2, 1, count, self.header.sector_size, name="VTOC2")
            segments.append(segment)
        return segments
    
    def get_directory_segments(self):
        b = self.bytes
        s = self.style
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(361, 8)
        segment = RawSectorsSegment(b[start:start+count], s[start:start+count], 361, 8, count, 128, 3, self.header.sector_size, name="Directory")
        segments.append(segment)
        return segments
    
    def get_file_segment(self, dirent):
        byte_order = []
        dirent.start_read(self)
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
