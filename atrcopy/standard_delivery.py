import numpy as np

from . import errors
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
            raise errors.InvalidDiskImage("No %s boot header" % self.file_format)

    def __str__(self):
        return "Standard Delivery Boot Disk (size=%d (%dx%dB)" % (self.file_format, self.image_size, self.max_sectors, self.sector_size)

    def check_size(self, size):
        if size != 143360:
            raise errors.InvalidDiskImage("Incorrect size for Standard Delivery image")
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
            run_addr = segments[0].origin

        chunks = []

        for s in segments:
            # find size in 256 byte chunks that start on a page boundary
            # since the loader only deals with page boundaries
            origin = s.origin
            chunk_start, padding = divmod(origin, 256)
            if (chunk_start == 0x20 or chunk_start == 0x40) and padding == 1:
                show_hgr = False
                padding = 0
            else:
                show_hgr = True
            size = ((len(s) + padding + 255) // 256) * 256
            chunk = np.zeros([size], dtype=np.uint8)
            chunk[padding:padding + len(s)] = s[:]
            chunks.append((chunk_start, chunk, show_hgr))
            print("segment: %s, pages=%d" % (str(s), len(chunk) // 256))
            log.debug(" last chunk=%s" % str(chunks[-1]))

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
        address_list = [0xd1]

        boot_sector = dsk.header.create_sector()
        boot_sector.sector_num = 0
        boot_sector.track_num = 1
        sector_list.append(boot_sector)
        first_page_1 = True

        for chunk_start, chunk_data, show_hgr in chunks:
            count = len(chunk_data) // 256
            if chunk_start == 0x20 and count == 32 and first_page_1:
                # Assume this is an HGR screen, use interesting load effect,
                # not the usual venetian blind
                chunk_hi = [0x20, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38, 0x3c, 0x21, 0x25, 0x29, 0x2d, 0x31, 0x35, 0x39, 0x3d, 0x22, 0x26, 0x2a, 0x2e, 0x32, 0x36, 0x3a, 0x3e, 0x23, 0x27, 0x2b, 0x2f, 0x33, 0x37, 0x3b, 0x3f]
                address_order = chunk_hi
            else:
                chunk_hi = range(chunk_start, chunk_start + count)
                if len(chunk_hi) > 2:
                    address_order = []
                    for n in range(0, count, 32):
                        subset = chunk_hi[n:n+32]
                        if len(subset) > 2:
                            address_order.extend([chunk_hi[n], 0xe0 + len(subset) - 1])
                        else:
                            address_order.extend(subset)
                else:
                    address_order = chunk_hi

            for n in range(count):
                i = (chunk_hi[n] - chunk_start) * 256
                sector = dsk.header.create_sector(chunk_data[i:i+256])
                sector.sector_num = dsk.header.sector_from_track(track, sector_order[index])
                count += 1
                #sector.sector_num = count
                sector_list.append(sector)
                # sector.data[0] = sector.sector_num
                # sector.data[1] = hi
                # sector.data[2:16] = 0xff
                log.debug("%s at %02x00: %s ..." % (sector_list[-1], address_list[-1], " ".join(["%02x" % h for h in chunk_data[i:i + 16]])))
                index += 1
                if index >= len(sector_order):
                    index = 0
                    track += 1
            address_list.extend(address_order)
            if show_hgr:
                if chunk_start == 0x40:
                    address_list.append(0xd2)
                elif chunk_start == 0x20:
                    if not first_page_1:
                        address_list.append(0xd1)
                    first_page_1 = False

        print("fstbt commands: %s" % ", ".join(["%02x" % i for i in address_list]))
        boot_code = get_fstbt_code(boot_sector.data, address_list, run_addr)

        dsk.write_sector_list(sector_list)

        return dsk

from . fstbt import fstbt

def get_fstbt_code(data, address_list, run_addr):
    pointer = len(fstbt)
    data[0:pointer] = np.fromstring(fstbt, dtype=np.uint8)
    hi, lo = divmod(run_addr, 256)
    data[pointer:pointer + 2] = (lo, hi)
    address_list.append(0xc0)  # last sector flag
    data[pointer + 2:pointer + 2 + len(address_list)] = address_list
