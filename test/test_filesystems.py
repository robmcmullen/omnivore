import glob

import numpy as np

from mock import *

from atrip.container import guess_container
from atrip.media_type import MediaType, guess_media_type
from atrip import errors

from atrip.media_types.atari_disks import *
from atrip.media_types.apple_disks import *

ext_to_valid_types = {
    '.atr': set([
        AtariDoubleDensity,
        AtariDoubleDensityHardDriveImage,
        AtariDoubleDensityShortBootSectors,
        AtariEnhancedDensity,
        AtariSingleDensity,
        AtariSingleDensityShortImage,
    ]),
    '.dsk': set([
        Apple16SectorDiskImage,
    ]),
}

class TestAtariDos2:
    base_path = None
    expected_mime = ""

    @pytest.mark.parametrize("pathname", sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../test_data/", "*"))))
    def test_test_data_dir(self, pathname):
        wrapped, ext = os.path.splitext(pathname)
        print(f"checking {pathname}")
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container = guess_container(sample_data)
        if container.compression_algorithm != "no compression":
            _, ext = os.path.splitext(wrapped)
        container.guess_media_type()
        print(ext, ext_to_valid_types)
        if ext in ext_to_valid_types:
            assert container.media.__class__ in ext_to_valid_types[ext]
        else:
            assert container.media.__class__ == MediaType


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrip.media_type")
    log.setLevel(logging.DEBUG)

    def check(pathname):
        print(f"checking {pathname}")
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container = guess_container(sample_data)
        container.guess_media_type()
        print(container.verbose_info)
        media = container.media
        media.guess_filesystem()
        print(media.filesystem)
        print(container.verbose_info)

    import sys
    import glob
    if len(sys.argv) > 1:
        images = sys.argv[1:]
    else:
        images = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../test_data/", "*")))
    for pathname in images:
        check(pathname)
