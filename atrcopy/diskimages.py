import numpy as np

from errors import *
from segments import SegmentData, EmptySegment, ObjSegment, RawSectorsSegment
from utils import to_numpy

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
            self.sector_size = 128
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
        self.files = []
        self.segments = []
        self.all_sane = True
        self.setup()

    def __len__(self):
        return len(self.rawdata)
    
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
        pass
    
    def get_directory(self):
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
        self.segments.append(RawSectorsSegment(r[i:], 1, self.header.max_sectors, self.header.image_size, 128, 3, self.header.sector_size, name="Raw disk sectors"))
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
    
    def find_file(self, filename):
        for dirent in self.files:
            if filename == dirent.get_filename():
                return self.get_file(dirent)
        return ""
    
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
        if nsec > max_sectors or nsec < 3:
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
