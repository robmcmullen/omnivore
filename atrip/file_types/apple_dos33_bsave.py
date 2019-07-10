import numpy as np

from .. import errors
from ..file_type import FileType
from ..segment import Segment
from ..style_bits import get_style_bits

import logging
log = logging.getLogger(__name__)


class Dos33Bsave(FileType):
    """Parse a binary chunk into segments according to the DOS 3.3 binary
    dump format
    """
    ui_name = "Apple DOS 3.3 Object File"

    def calc_segments(self):
        """Convenience method used by subclasses to create any sub-segments
        within this segment.

        """
        origin = self[0] + 256 * self[1]
        expected_count = self[2] + 256 * self[3]
        count = len(self) - 4
        if count != expected_count:
            raise errors.InvalidBinaryFile(f"Extra data after BSAVE segment: found {count}, header specifies {expected_count} bytes")
        s = Segment(self, 4, name=f"BSAVE data: ${count:04x}@${origin:04x}", origin=origin, length=count)
        return [s]
