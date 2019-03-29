import numpy as np

from .. import errors
from ..media_type import DiskImage

import logging
log = logging.getLogger(__name__)


class Apple16SectorDiskImage(DiskImage):
    pretty_name = "Apple ][ Floppy Disk Image (16 sector tracks)"
    sector_size = 256
    expected_size = 143360
