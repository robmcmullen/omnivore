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

    extra_serializable_attributes = ['num_sectors:int', 'first_directory:int', 'max_sectors:int', 'ts_pairs:int', 'dos_release:int', 'last_track_num:int', 'track_alloc_dir:int']

    def init_empty(self):
        super().init_empty()
        self.num_sectors = 0
        self.first_directory = -1
        self.max_sectors = 34 * 16
        self.ts_pairs = -1
        self.dos_release = -1
        self.last_track_num = 34
        self.track_alloc_dir = -1

    def sector_from_track(self, track, sector):
        return (track * self.sectors_per_track) + sector

    def follow_track_sector_pointers(self, track, sector, payload_offset, payload_size):
        """Calculate offsets into the media by following the track/sector
        pointers in the header of each sector, starting at the specified
        track/sector
        """
        offsets = np.empty(self.expected_size, dtype=np.uint32)
        offset_count = 0
        sector = self.sector_from_track(track, sector)
        print(f"starting at sector {sector}")
        while sector > 0:
            pos, count = self.get_index_of_sector(sector)
            offsets[offset_count:offset_count + payload_size] = np.arange(pos + payload_offset, pos + payload_offset + payload_size, dtype=np.int32)
            offset_count += payload_size
            t = self[pos + 1]
            s = self[pos + 2]
            next_sector = self.sector_from_track(t, s)
            print(f"sector: {sector}, pos={pos}, next={next_sector}")
            sector = next_sector
        subset = offsets[0:offset_count].copy()
        return subset

    def follow_track_sector_list(self, ts_segment):
        """Calculate offsets into the media by following the track/sector
        values in the given list of track/sector numbers.

        Each track/sector pair is two bytes in the list.
        """
        offsets = np.empty(self.expected_size, dtype=np.uint32)
        offset_count = 0
        index = 0
        while index < len(ts_segment):
            track = ts_segment[index]
            if track == 0:
                break
            sector = ts_segment[index + 1]
            index += 2
            sector = self.sector_from_track(track, sector)
            pos, count = self.get_index_of_sector(sector)
            print(f"sector: {sector}, pos={pos}, count={count}")
            offsets[offset_count:offset_count + count] = np.arange(pos, pos + count, dtype=np.int32)
            offset_count += count
        subset = offsets[0:offset_count].copy()
        return subset
