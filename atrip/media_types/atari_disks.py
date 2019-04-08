import numpy as np

from .. import errors
from ..media_type import DiskImage
from ..segment import Segment

import logging
log = logging.getLogger(__name__)


class AtrHeader(Segment):
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

    def __init__(self, container):
        Segment.__init__(self, container, 0, name="ATR Header", length=16)
        header = container[0:16]
        if len(header) == 16:
            values = header.view(dtype=self.format)[0]
            if values[0] != 0x296:
                raise errors.InvalidHeader("no ATR header magic value")
            self.image_size = (int(values[3]) * 256 * 256 + int(values[1])) * 16
            self.sector_size = int(values[2])
            self.crc = int(values[4])
            self.unused = int(values[5])
            self.flags = int(values[6])
        else:
            raise errors.InvalidHeader("incorrect AHC header size of %d" % len(bytes))

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

    def check_media(self, media):
        if self.sector_size != media.sector_size:
            raise errors.InvalidHeader("ExpectedMismatch between sector sizes: header claims {self.sector_size}, expected {media.sector_size} for {media.pretty_name}")
        media_size = len(media) - 16
        if self.image_size != media_size:
            raise errors.InvalidHeader("Invalid media size: header claims {self.image_size}, expected {media_size} for {media.pretty_name}")


class AtariSingleDensity(DiskImage):
    pretty_name = "Atari SD (90K) Floppy Disk Image"
    sector_size = 128
    expected_size = 92160

    def check_header(self):
        if self.header.sector_size != self.sector_size:
            raise errors.InvalidMediaSize(f"Sector size {self.header.sector_size} invalid for {self.pretty_name}")

    def calc_header(self, container):
        header_data = container[0:16]
        if len(header_data) == 16:
            try:
                header = AtrHeader(container)
            except errors.InvalidHeader:
                header = None
        else:
            raise errors.InvalidHeader(f"file size {len(data)} small to be {self.pretty_name}")
        return header


class AtariSingleDensityShortImage(AtariSingleDensity):
    pretty_name = "Atari SD Non-Standard Image"

    def check_disk_size(self):
        size = len(self)
        if size >= self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} must be less than size {self.expected_size}")

    def check_magic(self):
        # Must have an ATR header for this to be a disk image
        if self.header is None:
            raise errors.InvalidHeader("Must have an ATR header for a non-standard image size")
        flag = self[0:2].view(dtype='<u2')
        if flag == 0xffff:
            raise errors.InvalidHeader("Appears to be an executable")


class AtariEnhancedDensity(AtariSingleDensity):
    pretty_name = "Atari ED (130K) Floppy Disk Image"
    sector_size = 128
    expected_size = 133120


class AtariDoubleDensity(AtariSingleDensity):
    pretty_name = "Atari DD (180K) Floppy Disk Image"
    sector_size = 256
    expected_size = 184320


class AtariDoubleDensityShortBootSectors(AtariDoubleDensity):
    pretty_name = "Atari DD (180K) Floppy Disk Image (Short Boot Sectors)"
    expected_size = 183936
    initial_sector_size = 128
    num_initial_sectors = 3

    def calc_num_sectors(self):
        size = len(self)
        initial_size = self.initial_sector_size * self.num_initial_sectors
        remaining_size = size - initial_size
        if remaining_size % self.sector_size != 0:
            raise errors.InvalidMediaSize("ATR image not an integer number of sectors")
        return ((size - initial_size) // self.sector_size) + self.num_initial_sectors

    def get_index_of_sector(self, sector):
        if not self.sector_is_valid(sector):
            raise errors.ByteNotInFile166("Sector %d out of range" % sector)
        if sector <= self.num_initial_sectors:
            pos = self.num_initial_sectors * (sector - 1)
            size = self.initial_sector_size
        else:
            pos = self.num_initial_sectors * self.initial_sector_size + (sector - 1 - self.num_initial_sectors) * self.sector_size
            size = self.sector_size
        pos += self.header_length
        return pos, size


class AtariDoubleDensityHardDriveImage(AtariDoubleDensity):
    pretty_name = "Atari DD Hard Drive Image"

    def check_disk_size(self):
        size = len(self)
        if size <= self.expected_size:
            raise errors.InvalidMediaSize(f"{self.pretty_name} must be greater than size {self.expected_size}")


