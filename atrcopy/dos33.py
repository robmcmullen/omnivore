import numpy as np

from errors import *
from diskimages import DiskImageBase
from segments import DefaultSegment, EmptySegment, ObjSegment, RawSectorsSegment, SegmentSaver

import logging
log = logging.getLogger(__name__)


class Dos33Header(object):
    file_format = "DOS 3.3"

    def __init__(self):
        self.header_offset = 0
        self.image_size = 143360
        self.max_sectors = 35 * 16
        self.sector_size = 256
    
    def __str__(self):
        return "%s Disk Image (size=%d (%dx%db)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)
    
    def __len__(self):
        return 0
    
    def to_array(self):
        raw = np.zeros([0], dtype=np.uint8)
        return raw

    def check_size(self, size):
        if size != self.image_size:
            raise InvalidDiskImage("Incorrect size for DOS 3.3 image")

    def strict_check(self, image):
        size = len(image)
        if size in [143360]:
            return
        raise InvalidDiskImage("Incorrect size for DOS 3.3 image")


class Dos33DiskImage(DiskImageBase):
    def __init__(self, rawdata, filename=""):
        DiskImageBase.__init__(self, rawdata, filename)

    def __str__(self):
        return str(self.header)
    
    def read_header(self):
        self.header = Dos33Header()
    
    def get_boot_segments(self):
        return []
