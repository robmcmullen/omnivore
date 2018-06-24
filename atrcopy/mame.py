import zipfile

import numpy as np

from . import errors
from .segments import SegmentData, EmptySegment, ObjSegment
from .diskimages import DiskImageBase
from .utils import to_numpy

import logging
log = logging.getLogger(__name__)


class MameZipImage(DiskImageBase):
    def __init__(self, rawdata, filename=""):
        self.zipdata = rawdata
        fh = self.zipdata.bufferedio
        if zipfile.is_zipfile(fh):
            with zipfile.ZipFile(fh) as zf:
                self.check_zip_size(zf)
                self.create_rawdata(zf)
        else:
            raise errors.InvalidDiskImage("Not a MAME zip file")
        DiskImageBase.__init__(self, self.rawdata, filename)

    def __str__(self):
        return "MAME Zip file, %d ROMs, orig_size=%d, uncompressed=%d" % (len(self.zip_segment_info), len(self.zipdata), len(self.rawdata))

    def setup(self):
        self.check_size()

    def strict_check(self):
        pass

    def relaxed_check(self):
        pass

    def check_zip_size(self, zf):
        for item in zf.infolist():
            _, r = divmod(item.file_size, 16)
            if r > 0:
                raise errors.InvalidDiskImage("zip entry not 16 byte multiple")

    def create_rawdata(self, zf):
        roms = []
        segment_info = []
        offset = 0
        for item in zf.infolist():
            rom = np.fromstring(zf.open(item).read(), dtype=np.uint8)
            roms.append(rom)
            segment_info.append((offset, item.file_size, item.filename, item.CRC))
            offset += item.file_size
        data = np.concatenate(roms)
        self.zip_segment_info = segment_info
        self.rawdata = SegmentData(data)

    def check_size(self):
        pass

    def parse_segments(self):
        r = self.rawdata
        self.segments = []
        for offset, size, name, crc in self.zip_segment_info:
            end = offset + size
            self.segments.append(ObjSegment(r[offset:end], 0, offset, offset, end, name=name))
