import numpy as np

from errors import *
from diskimages import AtrHeader, DiskImageBase
from segments import DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, SegmentSaver

import logging
log = logging.getLogger(__name__)


class Dos33Header(AtrHeader):
    file_format = "DOS 3.3"

    def __init__(self):
        AtrHeader.__init__(self, None, 256, 0)
        self.header_offset = 0
        self.sector_order = range(16)
    
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


class Dos33DiskImage(DiskImageBase):
    def __init__(self, rawdata, filename=""):
        DiskImageBase.__init__(self, rawdata, filename)

    def __str__(self):
        return str(self.header)
    
    def read_header(self):
        self.header = Dos33Header()
    
    def get_boot_sector_info(self):
        # based on logic from a2server
        data, style = self.get_sectors(0)
        magic = data[0:4]
        if (magic == [1, 56, 176, 3]).all():
            raise InvalidDiskImage("ProDOS format found; not DOS 3.3 image")
        swap_order = False
        data, style = self.get_sectors(17 * 16)
        if data[3] == 3:
            if data[1] < 35 and data[2] < 16:
                data, style = self.get_sectors(17 * 16 + 14)
                if data[2] != 13:
                    swap_order = True
            else:
                raise InvalidDiskImage("Invalid VTOC location for DOS 3.3")

        print "swap", swap_order

    def get_boot_segments(self):
        return []


class ProdosHeader(Dos33Header):
    file_format = "ProDOS"


class ProdosDiskImage(Dos33DiskImage):
    def read_header(self):
        self.header = ProdosHeader()
        print "HI"

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

        print "swap", swap_order
