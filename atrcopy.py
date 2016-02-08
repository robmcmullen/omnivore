#!/usr/bin/env python


__version__ = "2.0.0"

import types

import numpy as np


class AtrError(RuntimeError):
    pass

class InvalidAtrHeader(AtrError):
    pass

class InvalidDiskImage(AtrError):
    pass

class LastDirent(AtrError):
    pass

class FileNumberMismatchError164(AtrError):
    pass

class ByteNotInFile166(AtrError):
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
        self.current_sector = 0
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
        self.current_sector = self.starting_sector
        self.current_read = self.num_sectors
    
    def read_sector(self, disk):
        raw, pos, size = disk.get_raw_bytes(self.current_sector)
        bytes, num_data_bytes = self.process_raw_sector(disk, raw)
        return bytes, self.current_sector == 0, pos, num_data_bytes

    def process_raw_sector(self, disk, raw):
        try:
            file_num = ord(raw[-3]) >> 2
        except TypeError:
            # if numpy data, don't need the ord()
            return self.process_raw_sector_numpy(disk, raw)
        if file_num != self.file_num:
            raise FileNumberMismatchError164()
        self.current_sector = ((ord(raw[-3]) & 0x3) << 8) + ord(raw[-2])
        num_bytes = ord(raw[-1])
        return raw[0:num_bytes], num_bytes

    def process_raw_sector_numpy(self, disk, raw):
        file_num = raw[-3] >> 2
        if file_num != self.file_num:
            raise FileNumberMismatchError164()
        self.current_sector = ((raw[-3] & 0x3) << 8) + raw[-2]
        num_bytes = raw[-1]
        return raw[0:num_bytes], num_bytes
    
    def get_filename(self):
        ext = ("." + self.ext) if self.ext else ""
        return self.filename + ext

class MydosDirent(AtrDirent):
    def process_raw_sector(self, disk, raw):
        self.current_read -= 1
        if self.current_read == 0:
            self.current_sector = 0
        else:
            self.current_sector += 1
            if self.current_sector == disk.first_vtoc:
                self.current_sector = disk.first_data_after_vtoc
        return raw


class InvalidBinaryFile(AtrError):
    pass



class DefaultSegment(object):
    debug = False
    
    def __init__(self, start_addr=0, data=None, name="All", error=None):
        self.start_addr = int(start_addr)  # force python int to decouple from possibly being a numpy datatype
        if data is None:
            data = np.fromstring("", dtype=np.uint8)
        else:
            data = to_numpy(data)
        self.data = data
        self.style = np.zeros_like(self.data, dtype=np.uint8)
        if self.debug:
            self.style = np.arange(len(self), dtype=np.uint8)
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
    
    def get_style_bits(self, match=False, comment=False):
        style_bits = 0
        if match:
            style_bits |= 1
        if comment:
            style_bits |= 0x80
        return style_bits
    
    def get_style_mask(self, match=False, comment=False):
        style_mask = 0xff
        if match:
            style_mask &= 0xfe
        if comment:
            style_mask &= 0x7f
        return style_mask
    
    def set_style_ranges(self, ranges, **kwargs):
        style_bits = self.get_style_bits(**kwargs)
        s = self.style
        for start, end in ranges:
            s[start:end] |= style_bits
    
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

class ObjSegment(DefaultSegment):
    def __init__(self, metadata_start, data_start, start_addr, end_addr, data, name="", error=None):
        DefaultSegment.__init__(self, start_addr, data, name, error)
        self.metadata_start = metadata_start
        self.data_start = data_start
    
    def __str__(self):
        count = len(self)
        s = "%s $%04x-$%04x ($%04x @ $%04x)" % (self.name, self.start_addr, self.start_addr + count, count, self.data_start)
        if self.error:
            s += " " + self.error
        return s

class RawSectorsSegment(DefaultSegment):
    def __init__(self, first_sector, num_sectors, count, data, **kwargs):
        DefaultSegment.__init__(self, 0, data, **kwargs)
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
    def __init__(self, byte_order, bytes, **kwargs):
        self.order = byte_order
        DefaultSegment.__init__(self, 0, bytes, **kwargs)
    
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
    def __init__(self, data):
        self.data = to_numpy(data)
        self.size = len(self.data)
        self.segments = []
        self.parse_segments()
    
    def __str__(self):
        return "\n".join(str(s) for s in self.segments) + "\n"
    
    def get_obj_segment(self, metadata_start, data_start, start_addr, end_addr, data, name=""):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an ObjSegment
        """
        return ObjSegment(metadata_start, data_start, start_addr, end_addr, data, name)
    
    def parse_segments(self):
        bytes = self.data
        pos = 0
        first = True
        while pos < self.size:
            header, = bytes[pos:pos+2].view(dtype=np.uint16)
            if header == 0xffff:
                # Apparently 0xffff header can appear in any segment, not just
                # the first.  Regardless, it is ignored everywhere.
                pos += 2
            elif first:
                raise InvalidBinaryFile
            first = False
            if len(bytes[pos:pos + 4]) < 4:
                self.segments.append(self.get_obj_segment(0, 0, bytes[pos:pos + 4], "Short Segment Header"))
                break
            start, end = bytes[pos:pos + 4].view(dtype=np.uint16)
            count = end - start + 1
            found = len(bytes[pos + 4:pos + 4 + count])
            if found < count:
                self.segments.append(self.get_obj_segment(pos, pos + 4, start, end, bytes[pos + 4:pos + 4 + count], "Incomplete Data"))
                break
            self.segments.append(self.get_obj_segment(pos, pos + 4, start, end, bytes[pos + 4:pos + 4 + count]))
            pos += 4 + count

class AtrFileSegment(ObjSegment):
    def __init__(self, dirent, data, error=None):
        ObjSegment.__init__(self, 0, data, error)
        self.dirent = dirent
    
    def __str__(self):
        s = str(self.dirent)
        if self.error:
            s += " " + self.error
        return s


class DiskImageBase(object):
    def __init__(self, bytes):
        self.bytes = to_numpy(bytes)
        self.header = None
        self.total_sectors = 0
        self.unused_sectors = 0
        self.files = []
        self.segments = []
        self.all_sane = True
        self.setup()
    
    def setup(self):
        self.size = np.alen(self.bytes)
        self.read_atr_header()
        self.check_size()
    
    def read_atr_header(self):
        bytes = self.bytes[0:16]
        try:
            self.header = AtrHeader(bytes)
        except InvalidAtrHeader:
            self.header = XfdHeader()
    
    def check_size(self):
        self.header.check_size(self.size)
    
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
        return self.bytes[pos:pos + size]
    
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
        if self.header.image_size > 0:
            self.segments.append(ObjSegment(0, 0, 0, self.header.atr_header_offset, self.bytes[0:self.header.atr_header_offset], name="%s Header" % self.header.file_format))
        self.segments.append(RawSectorsSegment(1, self.header.max_sectors, self.header.image_size, self.bytes[self.header.atr_header_offset:], name="Raw disk sectors"))


class BootDiskImage(DiskImageBase):
    def __str__(self):
        return "%s Boot Disk" % (self.header)
    
    def check_size(self):
        self.header.check_size(self.size)
        start, size = self.header.get_pos(1)
        i = self.header.atr_header_offset
        flag = self.bytes[i:i + 2].view(dtype='<u2')[0]
        if flag == 0xffff:
            raise InvalidDiskImage("Appears to be an executable")
        nsec = self.bytes[i + 1]
        bload = self.bytes[i + 2:i + 4].view(dtype='<u2')[0]
        binit = self.bytes[i + 4:i + 6].view(dtype='<u2')[0]
        blen, _ = self.header.get_pos(nsec + 1)
        print nsec, bload, binit, blen
        if not (bload < binit < bload + blen):
            raise InvalidDiskImage("Incorrect boot load/init parameters")


class AtariDosDiskImage(DiskImageBase):
    def __init__(self, bytes):
        self.first_vtoc = 360
        self.num_vtoc = 1
        self.vtoc2 = 0
        self.first_data_after_vtoc = 369
        DiskImageBase.__init__(self, bytes)
    
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
    
    def setup(self):
        self.size = np.alen(self.bytes)
        
        self.read_atr_header()
        self.check_size()
        self.get_vtoc()
        self.get_directory()
        if not self.all_sane:
            raise InvalidDiskImage("Invalid directory entries; may be boot disk")
    
    vtoc_type = np.dtype([
        ('code', 'u1'),
        ('total','<u2'),
        ('unused','<u2'),
        ])

    def get_vtoc(self):
        values = self.get_sectors(360)[0:5].view(dtype=self.vtoc_type)[0]  
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
        dir_bytes = self.get_sectors(361, 368)
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
    
    def get_file(self, dirent):
        segment = self.get_file_segment(dirent)
        return segment.tostring()
    
    def find_file(self, filename):
        for dirent in self.files:
            if filename == dirent.get_filename():
                return self.get_file(dirent)
        return ""
    
    def get_obj_segment(self, metadata_start, data_start, start_addr, end_addr, data, name):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an ObjSegment
        """
        return ObjSegment(metadata_start, data_start, start_addr, end_addr, data, name)
    
    def get_raw_sectors_segment(self, first_sector, num_sectors, count, data, **kwargs):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an RawSectorsSegment
        """
        return RawSectorsSegment(first_sector, num_sectors, count, data, **kwargs)
    
    def get_indexed_segment(self, byte_order, **kwargs):
        """Subclass use: override this method to create a custom segment.
        
        By default uses an IndexedByteSegment
        """
        return IndexedByteSegment(byte_order, self.bytes, **kwargs)
    
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
        values = self.get_sectors(360)[0:20].view(dtype=self.boot_record_type)[0]  
        flag = int(values[0])
        segments = []
        if flag == 0:
            num = int(values[1])
            addr = int(values[2])
            bytes = self.get_sectors(1, num)
            header = self.get_obj_segment(0, 0, addr, addr + 20, bytes[0:20], name="Boot Header")
            sectors = self.get_obj_segment(0, 0, addr, addr + len(bytes), bytes, name="Boot Sectors")
            code = self.get_obj_segment(0, 0, addr + 20, addr + len(bytes), bytes[20:], name="Boot Code")
            segments = [sectors, header, code]
        return segments
    
    def get_vtoc_segments(self):
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(self.first_vtoc, self.num_vtoc)
        segment = self.get_raw_sectors_segment(self.first_vtoc, self.num_vtoc, count, self.bytes[start:start+count], name="VTOC")
        segments.append(segment)
        if self.vtoc2 > 0:
            start, count = self.get_contiguous_sectors(self.vtoc2, 1)
            segment = self.get_raw_sectors_segment(self.vtoc2, 1, count, self.bytes[start:start+count], name="VTOC2")
            segments.append(segment)
        return segments
    
    def get_directory_segments(self):
        segments = []
        addr = 0
        start, count = self.get_contiguous_sectors(361, 8)
        segment = self.get_raw_sectors_segment(361, 8, count, self.bytes[start:start+count], name="Directory")
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
        segment = self.get_indexed_segment(byte_order, name=dirent.get_filename())
        return segment
    
    def get_file_segments(self):
        segments = []
        self.get_directory()
        for dirent in self.files:
            segment = self.get_file_segment(dirent)
            segments.append(segment)
        return segments
    
    def parse_segments(self):
        if self.header.image_size > 0:
            self.segments.append(self.get_obj_segment(0, 0, 0, self.header.atr_header_offset, self.bytes[0:self.header.atr_header_offset], name="%s Header" % self.header.file_format))
        self.segments.append(self.get_raw_sectors_segment(1, self.header.max_sectors, self.header.image_size, self.bytes[self.header.atr_header_offset:], name="Raw disk sectors"))
        self.segments.extend(self.get_boot_segments())
        self.segments.extend(self.get_vtoc_segments())
        self.segments.extend(self.get_directory_segments())
        self.segments.extend(self.get_file_segments())


class KBootImage(DiskImageBase):
    def __init__(self, bytes):
        self.exe_start = 0
        self.exe_size = 0
        DiskImageBase.__init__(self, bytes)

    def __str__(self):
        return "%s KBoot Format: %d byte executable" % (self.header, self.exe_size)
    
    def check_size(self):
        self.header.check_size(self.size)
        start, size = self.header.get_pos(4)
        i = self.header.atr_header_offset + 9
        count = self.bytes[i] + 256 * self.bytes[i+1] + 256 * 256 *self.bytes[i + 2]
        if start + count > self.size or start + count < self.size - 128:
            raise InvalidDiskImage("Doesn't seem to be KBoot header")
        self.exe_size = count
        self.exe_start = start
    
    def get_file_segment(self):
        return ObjSegment(0, 0, 0, self.exe_start, self.bytes[self.exe_start:self.exe_start + self.exe_size], name="KBoot Executable")
    
    def parse_segments(self):
        if self.header.image_size > 0:
            self.segments.append(ObjSegment(0, 0, 0, self.header.atr_header_offset, self.bytes[0:self.header.atr_header_offset], name="%s Header" % self.header.file_format))
        self.segments.append(RawSectorsSegment(1, self.header.max_sectors, self.header.image_size, self.bytes[self.header.atr_header_offset:], name="Raw disk sectors"))
        self.segments.append(self.get_file_segment())


def to_numpy(value):
    if type(value) is np.ndarray:
        return value
    elif type(value) is types.StringType:
        return np.fromstring(value, dtype=np.uint8)
    raise TypeError("Can't convert to numpy data")

def process(dirent, options):
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
            bytes = atr.get_file(dirent)
            with open(outfilename, "wb") as fh:
                fh.write(bytes)
    else:
        print dirent

if __name__ == "__main__":
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
                    for format in [KBootImage, AtariDosDiskImage, BootDiskImage]:
                        print "trying", format.__name__
                        try:
                            image = format(data)
                            print "%s: %s" % (filename, image)
                            break
                        except InvalidDiskImage:
                            pass
                except InvalidAtrHeader:
                    for format in [AtariDosDiskImage]:
                        try:
                            image = format(data)
                            print "%s: %s" % (filename, image)
                            break
                        except:
                            raise
                            #pass
            except:
                raise
                print "%s: Doesn't look like a supported disk image" % filename
                try:
                    image = AtariDosFile(data)
                except InvalidBinaryFile:
                    print "%s: Doesn't look like an XEX either" % filename
                continue
            if image is None:
                image = BootDiskImage(data)
            if options.segments:
                image.parse_segments()
                print "\n".join([str(a) for a in image.segments])
            elif image.files or options.force:
                for dirent in image.files:
                    try:
                        process(dirent, options)
                    except FileNumberMismatchError164:
                        print "Error 164: %s" % str(dirent)
                    except ByteNotInFile166:
                        print "Invalid sector for: %s" % str(dirent)

