import numpy as np

from .. import errors
from ..media_type import DiskImage

import logging
log = logging.getLogger(__name__)


class Apple16SectorDiskImage(DiskImage):
    ui_name = "Apple ][ Floppy Disk Image (16 sector tracks)"
    sector_size = 256
    expected_size = 143360
    sectors_per_track = 16
    starting_sector_label = 0

    def init_media_params(self):
        self.num_sectors = 0
        self.first_directory = -1
        self.max_sectors = 34 * 16
        self.ts_pairs = -1
        self.dos_release = -1
        self.last_track_num = 34
        self.track_alloc_dir = -1

    def sector_from_track(self, track, sector):
        return (track * self.sectors_per_track) + sector
