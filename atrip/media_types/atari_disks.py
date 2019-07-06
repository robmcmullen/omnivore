import numpy as np

from .. import errors
from ..media_type import DiskImage
from ..segment import Segment
from ..container import ContainerHeader

import logging
log = logging.getLogger(__name__)


class AtrHeader(ContainerHeader):
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

    def decode_from_bytes(self, header):
        values = header.view(dtype=self.format)[0]
        if values[0] != 0x296:
            raise errors.InvalidHeader("no ATR header magic value")
        self.image_size = (int(values[3]) * 256 * 256 + int(values[1])) * 16
        self.sector_size = int(values[2])
        self.crc = int(values[4])
        self.unused = int(values[5])
        self.flags = int(values[6])

    def encode_to_bytes(self, raw):
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


class AtariSingleDensity(DiskImage):
    ui_name = "Atari SD (90K) Floppy Disk Image"
    sector_size = 128
    expected_size = 92160

    def check_header(self, header):
        if header.sector_size != self.sector_size:
            raise errors.InvalidMediaSize(f"Sector size {header.sector_size} invalid for {self.ui_name}")

    def calc_header(self, container):
        header_data = container[0:16]
        if len(header_data) == 16:
            try:
                header = AtrHeader(container)
            except errors.InvalidHeader:
                header = None
        else:
            raise errors.InvalidHeader(f"file size {len(header_data)} small to be {self.ui_name}")
        return header


class AtariSingleDensityShortImage(AtariSingleDensity):
    ui_name = "Atari SD Non-Standard Image"

    def check_disk_size(self):
        size = len(self)
        if size >= self.expected_size:
            raise errors.InvalidMediaSize(f"{self.ui_name} must be less than size {self.expected_size}")

    def check_magic(self):
        # Must have an ATR header for this to be a disk image
        if self.container.header is None:
            raise errors.InvalidHeader("Must have an ATR header for a non-standard image size")
        flag = self[0:2].view(dtype='<u2')
        if flag == 0xffff:
            raise errors.InvalidHeader("Appears to be an executable")


class AtariEnhancedDensity(AtariSingleDensity):
    ui_name = "Atari ED (130K) Floppy Disk Image"
    sector_size = 128
    expected_size = 133120


class AtariDoubleDensity(AtariSingleDensity):
    ui_name = "Atari DD (180K) Floppy Disk Image"
    sector_size = 256
    expected_size = 184320


class AtariDoubleDensityShortBootSectors(AtariDoubleDensity):
    ui_name = "Atari DD (180K) Floppy Disk Image (Short Boot Sectors)"
    expected_size = 183936
    initial_sector_size = 128
    num_initial_sectors = 3

    def calc_num_sectors(self):
        size = len(self)
        print(size)
        initial_size = self.initial_sector_size * self.num_initial_sectors
        remaining_size = size - initial_size
        if remaining_size % self.sector_size != 0:
            raise errors.InvalidMediaSize("ATR image not an integer number of sectors")
        return ((size - initial_size) // self.sector_size) + self.num_initial_sectors

    def get_index_of_sector(self, sector):
        if not self.is_sector_valid(sector):
            raise errors.ByteNotInFile166("Sector %d out of range" % sector)
        if sector <= self.num_initial_sectors:
            pos = self.num_initial_sectors * (sector - 1)
            size = self.initial_sector_size
        else:
            pos = self.num_initial_sectors * self.initial_sector_size + (sector - 1 - self.num_initial_sectors) * self.sector_size
            size = self.sector_size
        return pos, size


class AtariDoubleDensityHardDriveImage(AtariDoubleDensity):
    ui_name = "Atari DD Hard Drive Image"

    def check_disk_size(self):
        size = len(self)
        if size <= self.expected_size:
            raise errors.InvalidMediaSize(f"{self.ui_name} must be greater than size {self.expected_size}")


