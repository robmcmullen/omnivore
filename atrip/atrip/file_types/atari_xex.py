import numpy as np

from .. import errors
from ..file_type import FileType
from ..segment import Segment
from ..style_bits import get_style_bits

import logging
log = logging.getLogger(__name__)

try:  # Expensive debugging
    _xd = _expensive_debugging
except NameError:
    _xd = False


class RunAddressSegment(Segment):
    @property
    def run_address(self):
        return self[0] + 256 * self[1]


class InitAddressSegment(Segment):
    @property
    def init_address(self):
        return self[0] + 256 * self[1]


class ObjSegment(Segment):
    def __init__(self, parent, offset, name, length):
        Segment.__init__(self, parent, offset, name=name, length=length)

    def calc_segments(self):
        """Convenience method used by subclasses to create any sub-segments
        within this segment.

        """
        start = self[0] + 256 * self[1]
        end = self[2] + 256 * self[3]
        count = end - start + 1
        if start == 0x2e0:
            target = self[4] + 256 * self[5]
            s = RunAddressSegment(self, 4, origin=start, name=f"RUNAD: JMP ${target:04x}", length=2)
        elif start == 0x2e2:
            target = self[4] + 256 * self[5]
            s = InitAddressSegment(self, 4, origin=start, name=f"INITAD: JSR ${target:04x}", length=2)
        else:
            s = Segment(self, 4, name=f"[${start:04x}-${end:04x}]", origin=start, length=count)
        return [s]


class AtariObjectFile(FileType):
    """Parse a binary chunk into segments according to the Atari DOS object
    file format.
    
    Ref: http://www.atarimax.com/jindroush.atari.org/afmtexe.html
    """
    ui_name = "Atari 8-bit Object File"

    def calc_segments(self):
        segments = []
        size = len(self)
        b = self.data
        pos = 0
        first = True
        if _xd: log.debug("Initial parsing: size=%d" % size)
        while pos < size:
            if pos + 1 < size:
                header, = b[pos:pos+2].view(dtype='<u2')
            else:
                segments.append(Segment(self, pos, 0, "Incomplete Data", length=1))
                break
            if header == 0xffff:
                # Apparently 0xffff header can appear in any segment, not just
                # the first.  Regardless, it is ignored everywhere.
                pos += 2
                first = False
                continue
            elif first:
                raise errors.InvalidBinaryFile("Object file doesn't start with 0xffff")
            if _xd: log.debug("header parsing: header=0x%x" % header)
            if len(b[pos:pos + 4]) < 4:
                segments.append(Segment(self, 0, 0, "Short Segment Header", length=len(b[pos:pos + 4])))
                break
            start, end = b[pos:pos + 4].view(dtype='<u2')
            if end < start:
                raise errors.InvalidBinaryFile("Nonsensical start and end addresses")
            count = end - start + 1
            found = len(b[pos + 4:pos + 4 + count])
            if found < count:
                segments.append(Segment(self, 4 + count, pos, pos + 4, start, end, "Incomplete Data"))
                break
            s = ObjSegment(self, pos, f"Segment #{len(segments) + 1}", length=4 + count)
            segments.append(s)
            pos += 4 + count
        return segments
