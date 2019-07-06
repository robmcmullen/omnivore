import glob

import numpy as np

from mock import *

from atrip.container import guess_container, load
from atrip.media_type import Media, guess_media_type
from atrip import errors

from atrip.media_types.atari_disks import *
from atrip.media_types.apple_disks import *

class TestDiskImage:

    @pytest.mark.parametrize("filename,sector_size,sectors", [
        ("dos_sd_test1.atr", 128, [(1,3), (360,1), (361,8)]),
        ("dos_ed_test1.atr", 128, [(1,3), (360,1), (361,8)]),
    ])
    def test_contiguous_sectors(self, filename, sector_size, sectors):
        pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
        container = load(pathname)
        media = container.media

        for start, count in sectors:
            # grab sectors
            segment = media.get_contiguous_sectors(start, count)
            # 16 byte ATR header, first byte of sector 1 is byte 16
            assert np.array_equal(segment.container_offset, np.arange(16 + (start - 1) * sector_size, 16 + (start + count - 1)*sector_size))

    def test_ed_sectors(self):
        pathname = os.path.join(os.path.dirname(__file__), "../samples/dos_ed_test1.atr")
        container = load(pathname)
        media = container.media

        # get vtoc + vtoc2
        boot = media.get_sector_list([360,1024])
        assert np.array_equal(boot.container_offset[0:128], np.arange(16 + (360 - 1) * 128, 16 + 360*128))
        assert np.array_equal(boot.container_offset[128:256], np.arange(16 + (1024 - 1) * 128, 16 + 1024*128))


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrip.media_type")
    log.setLevel(logging.DEBUG)

    def check(pathname):
        print(f"checking {pathname}")
        container = load(pathname)
        print(container.verbose_info)
        media = container.media
        print(media)
        boot = media.get_contiguous_sectors(1, 3)
        print(boot)
        print(boot.container_offset)

    import sys
    import glob
    if len(sys.argv) > 1:
        images = sys.argv[1:]
    else:
        images = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../samples/", "*")))
    for pathname in images:
        check(pathname)
