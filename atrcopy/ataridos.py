import numpy as np

from errors import *
from diskimages import DiskImageBase
from segments import EmptySegment, ObjSegment, RawSectorsSegment, DefaultSegment, SegmentSaver
from utils import to_numpy

import logging
log = logging.getLogger(__name__)


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
        flags = self.summary()
        return "File #%-2d (%s) %03d %-8s%-3s  %03d" % (self.file_num, flags, self.starting_sector, self.filename, self.ext, self.num_sectors)
    
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
    export_data_name = "Atari 8-bit Executable"
    export_extensions = [".xex"]


class XexSegment(ObjSegment):
    savers = [SegmentSaver, XexSegmentSaver]


class AtariDosFile(object):
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
        pos = 0
        first = True
        log.debug("Initial parsing: size=%d" % self.size)
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
                raise InvalidBinaryFile
            log.debug("header parsing: header=0x%x" % header)
            if len(b[pos:pos + 4]) < 4:
                self.segments.append(ObjSegment(r[pos:pos + 4], 0, 0, 0, len(b[pos:pos + 4]), "Short Segment Header"))
                break
            start, end = b[pos:pos + 4].view(dtype='<u2')
            if end < start:
                raise InvalidBinaryFile
            count = end - start + 1
            found = len(b[pos + 4:pos + 4 + count])
            if found < count:
                self.segments.append(ObjSegment(r[pos + 4:pos + 4 + count], pos, pos + 4, start, end, "Incomplete Data"))
                break
            self.segments.append(ObjSegment(r[pos + 4:pos + 4 + count], pos, pos + 4, start, end))
            pos += 4 + count


class AtariDosDiskImage(DiskImageBase):
    def __init__(self, *args, **kwargs):
        self.first_vtoc = 360
        self.num_vtoc = 1
        self.vtoc2 = 0
        self.first_data_after_vtoc = 369
        DiskImageBase.__init__(self, *args, **kwargs)
    
    def __str__(self):
        return "%s Atari DOS Format: %d usable sectors (%d free), %d files" % (self.header, self.total_sectors, self.unused_sectors, len(self.files))
    
    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    def calc_vtoc_code(self):
        # From AA post: http://atariage.com/forums/topic/179868-mydos-vtoc-size/
        num = 1 + (self.total_sectors + 80) / (self.header.sector_size * 8)
        if self.header.sector_size == 128:
            if num == 1:
                code = 2
            else:
                if num & 1:
                    num += 1
                code = ((num + 1) / 2) + 2
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
            raise InvalidDiskImage("Invalid number of VTOC sectors: %d" % num)
        
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
        segments.append(segment)
        if self.vtoc2 > 0:
            start, count = self.get_contiguous_sectors(self.vtoc2, 1)
            segment = RawSectorsSegment(r[start:start+count], self.vtoc2, 1, count, self.header.sector_size, name="VTOC2")
            segments.append(segment)
        return segments
    
    def get_directory_segments(self):
        r = self.rawdata
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(361, 8)
        segment = RawSectorsSegment(r[start:start+count], 361, 8, count, 128, 3, self.header.sector_size, name="Directory")
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
            name = "%s %ds@%d" % (dirent.get_filename(), dirent.num_sectors, dirent.starting_sector)
            verbose_name = "%s (%d sectors, first@%d) %s" % (dirent.get_filename(), dirent.num_sectors, dirent.starting_sector, dirent.verbose_info)
            raw = self.rawdata.get_indexed(byte_order)
            segment = DefaultSegment(raw, name=name, verbose_name=verbose_name)
        else:
            segment = EmptySegment(self.rawdata, name=dirent.get_filename())
        return segment
    
    def get_file_segments(self):
        segments_in = DiskImageBase.get_file_segments(self)
        segments_out = []
        for segment in segments_in:
            segments_out.append(segment)
            try:
                binary = AtariDosFile(segment.rawdata)
                segments_out.extend(binary.segments)
            except InvalidBinaryFile:
                log.debug("%s not a binary file; skipping segment generation" % str(segment))
        return segments_out

def get_xex(segments, runaddr):
    total = 2
    for s in segments:
        total += 4 + len(s)
    total += 6
    bytes = np.zeros([total], dtype=np.uint8)
    bytes[0:2] = 0xff # FFFF header
    i = 2
    for s in segments:
        words = bytes[i:i+4].view(dtype='<u2')
        words[0] = s.start_addr
        words[1] = s.start_addr + len(s) - 1
        i += 4
        bytes[i:i + len(s)] = s[:]
        i += len(s)
    words = bytes[i:i+6].view(dtype='<u2')
    words[0] = 0x2e0
    words[1] = 0x2e1
    words[2] = runaddr
    return bytes
