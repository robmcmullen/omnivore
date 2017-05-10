from __future__ import absolute_import
from __future__ import division
import numpy as np

from .errors import *
from .segments import SegmentData
from .diskimages import BaseHeader, DiskImageBase

import logging
log = logging.getLogger(__name__)


class StandardDeliveryHeader(BaseHeader):
    file_format = "Apple ][ Standard Delivery"

    def __init__(self, bytes=None, sector_size=256, create=False):
        BaseHeader.__init__(self, sector_size, create=create)
        if bytes is None:
            return

        data = bytes[0:5]
        if np.all(data == (0x01, 0xa8, 0xee, 0x06, 0x08)):
            log.debug("Found 48k loader")
        else:
            raise InvalidDiskImage("No %s boot header" % self.file_format)

    def __str__(self):
        return "Standard Delivery Boot Disk (size=%d (%dx%dB)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)

    def check_size(self, size):
        if size != 143360:
            raise InvalidDiskImage("Incorrect size for Standard Delivery image")
        self.image_size = size
        self.tracks_per_disk = 35
        self.sectors_per_track = 16
        self.max_sectors = self.tracks_per_disk * self.sectors_per_track


class StandardDeliveryImage(DiskImageBase):
    def __str__(self):
        return str(self.header)

    def read_header(self):
        self.header = StandardDeliveryHeader(self.bytes[0:256])

    @classmethod
    def new_header(cls, diskimage, format="DSK"):
        if format.lower() == "dsk":
            header = StandardDeliveryHeader(create=True)
            header.check_size(diskimage.size)
        else:
            raise RuntimeError("Unknown header type %s" % format)
        return header

    def check_size(self):
        pass

    def get_boot_sector_info(self):
        pass

    def get_vtoc(self):
        pass

    def get_directory(self, directory=None):
        pass

    @classmethod
    def create_boot_image(cls, segments, run_addr=None):
        raw = SegmentData(np.zeros([143360], dtype=np.uint8))
        dsk = cls(raw, create=True)
        if run_addr is None:
            run_addr = segments[0].start_addr

        chunks = []

        for s in segments:
            # find size in 256 byte chunks that start on a page boundary
            # since the loader only deals with page boundaries
            origin = s.start_addr
            chunk_start, padding = divmod(origin, 256)
            size = ((len(s) + padding + 255) // 256) * 256
            chunk = np.zeros([size], dtype=np.uint8)
            chunk[padding:padding + len(s)] = s[:]
            chunks.append((chunk_start, chunk))
            print("segment: %s, chunk=%s" % (str(s), str(chunks[-1])))

        # break up the chunks into sectors

        # NOTE: fstbt implied that the sector order was staggered, but in
        # AppleWin, by trial and error, works with the following order

        # index = 1  # on the first track, sector 0 is reserved for boot sector
        # sector_order = [0, 2, 4, 6, 8, 10, 12, 14, 1, 3, 5, 7, 9, 11, 13, 15]

        index = 1
        sector_order = [0, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 15]
        track = 0
        count = 0

        sector_list = []
        address_list = []

        boot_sector = dsk.header.create_sector()
        boot_sector.sector_num = 0
        boot_sector.track_num = 1
        sector_list.append(boot_sector)

        for chunk_start, chunk_data in chunks:
            i = 0
            hi = chunk_start
            while i < len(chunk_data):
                sector = dsk.header.create_sector(chunk_data[i:i+256])
                sector.sector_num = dsk.header.sector_from_track(track, sector_order[index])
                count += 1
                #sector.sector_num = count
                sector_list.append(sector)
                address_list.append(hi)
                # sector.data[0] = sector.sector_num
                # sector.data[1] = hi
                # sector.data[2:16] = 0xff
                print("%s at %02x00: %s ..." % (sector_list[-1], address_list[-1], " ".join(["%02x" % h for h in chunk_data[i:i + 16]])))
                index += 1
                if index >= len(sector_order):
                    index = 0
                    track += 1
                i += 256
                hi += 1

        print("address list %s" % str(address_list))
        boot_code = get_fstbt_code(boot_sector.data, address_list, run_addr)

        dsk.write_sector_list(sector_list)

        return dsk


# fast boot code minus final jump address and sector address table
fstbt_64k = b'\x01\xa8\xee\x06\x08\xadM\x08\xc9\xc0\xf0?\x85\x27\xc8\xc0\x10\x90\t\xf0\x05 .\x08\xa8,\xa0\x01\x84=\xc8\xa5\x27\xf0\xdf\x8a {\xf8\t\xc0H\xa9[H`\xe6A\x06@ 6\x08\x18 ;\x08\xe6@\xa5@)\x03*\x05+\xa8\xb9\x80\xc0\xa90L\xa8\xfcL'

fstbt_64k_hgr = b'\x01\xa8,P\xc0,R\xc0,W\xc0\xee\x0f\x08\xadV\x08\xc9\xc0\xf0?\x85\x27\xc8\xc0\x10\x90\t\xf0\x05 7\x08\xa8,\xa0\x01\x84=\xc8\xa5\x27\xf0\xdf\x8a {\xf8\t\xc0H\xa9[H`\xe6A\x06@ ?\x08\x18 D\x08\xe6@\xa5@)\x03*\x05+\xa8\xb9\x80\xc0\xa90L\xa8\xfcL'

def get_fstbt_code(data, address_list, run_addr):
    code = fstbt_64k_hgr
    pointer = len(code)
    data[0:pointer] = np.fromstring(code, dtype=np.uint8)
    hi, lo = divmod(run_addr, 256)
    data[pointer:pointer + 2] = (lo, hi)
    address_list.append(0xc0)  # last sector flag
    data[pointer + 2:pointer + 2 + len(address_list)] = address_list
