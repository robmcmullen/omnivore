import os
import glob

# Include maproom directory so that maproom modules can be imported normally
import sys
module_dir = os.path.realpath(os.path.abspath(".."))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

# print(sys.path)

import pytest
try:
    slow = pytest.mark.skipif(
        not pytest.config.getoption("--runslow"),
        reason="need --runslow option to run"
        )
except AttributeError:
    # pytest doesn't load the config module when not run using py.test
    # skip this check when running a test_*.py from the command line
    import functools
    slow = lambda a: functools.partial(print, "skipping slow test %s" % repr(a))

# Turn logging on by default at the DEBUG level for tests
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

import numpy as np
from numpy.testing import assert_almost_equal

from atrip.media_type import Media
from atrip.media_types.atari_disks import *
from atrip.media_types.atari_tapes import *
from atrip.media_types.apple_disks import *

sample_atari_files = [
    "../samples/dos_sd_test1.atr",
    "../samples/dos_ed_test1.atr",
    "../samples/dos_dd_test1.atr",
    "../samples/mydos_sd_mydos4534.dcm",
]

globbed_sample_atari_files = []
for s in sample_atari_files:
    possiblities = glob.glob(s + "*")
    globbed_sample_atari_files.extend(possiblities)


sample_atari_collections = [
    "../samples/dos_sd_test_collection.zip",
    "../samples/dos_sd_test_collection.tar",
]

globbed_sample_atari_collections = []
for s in sample_atari_collections:
    possiblities = glob.glob(s + "*")
    globbed_sample_atari_collections.extend(possiblities)


ext_to_valid_types = {
    '.atr': set([
        AtariDoubleDensity,
        AtariDoubleDensityHardDriveImage,
        AtariDoubleDensityShortBootSectors,
        AtariEnhancedDensity,
        AtariSingleDensity,
        AtariSingleDensityShortImage,
    ]),
    '.dcm': set([
        AtariDoubleDensity,
        AtariEnhancedDensity,
        AtariSingleDensity,
    ]),
    '.xfd': set([
        AtariDoubleDensity,
        AtariEnhancedDensity,
        AtariSingleDensity,
    ]),
    '.cas': set([
        AtariCassetteImage,
    ]),
    '.dsk': set([
        Apple16SectorDiskImage,
    ]),
}

def find_uncompressed_ext(pathname):
    wrapped, ext = os.path.splitext(pathname)
    while ext in [".gz", ".bz2", ".lz4", ".xz", ".lzma", ".Z"]:
        wrapped, ext = os.path.splitext(wrapped)
    ext = ext.lower()
    return ext

def is_expected_media(container, pathname):
    ext = find_uncompressed_ext(pathname)
    print(f"found ext {ext}")
    print(ext, ext_to_valid_types)
    if ext in ext_to_valid_types:
        assert container.media.__class__ in ext_to_valid_types[ext]
    else:
        assert container.media.__class__ == Media
