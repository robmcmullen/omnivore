import glob

import numpy as np

from mock import *

from atrcopy.container import guess_container
from atrcopy.media_type import MediaType, guess_media_type
from atrcopy import errors

from atrcopy.media_types.atari_disks import *
from atrcopy.media_types.apple_disks import *

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

class TestMediaTypesInTestDataDir:
    base_path = None
    expected_mime = ""

    def test_test_data_dir(self):
        for pathname in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../test_data/", "*"))):
            wrapped, ext = os.path.splitext(pathname)
            print(f"checking {pathname}")
            sample_data = np.fromfile(pathname, dtype=np.uint8)
            container, uncompressed_data = guess_container(sample_data)
            if container:
                _, ext = os.path.splitext(wrapped)
            print(len(uncompressed_data))
            media = guess_media_type(uncompressed_data)
            print(f"{pathname}: {media}")
            if ext in ext_to_valid_types:
                assert media.__class__ in ext_to_valid_types[ext]
            else:
                assert media.__class__ == MediaType


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("atrcopy.media_type")
    log.setLevel(logging.DEBUG)

    import glob
    for pathname in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "../test_data/", "*"))):
        print(f"checking {pathname}")
        sample_data = np.fromfile(pathname, dtype=np.uint8)
        container, uncompressed_data = guess_container(sample_data)
        # if container: print(container.name)
        print(len(uncompressed_data))
        media = guess_media_type(uncompressed_data)
        print(f"{pathname}: {media}")
