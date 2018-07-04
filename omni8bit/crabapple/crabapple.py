import ctypes
import time

import numpy as np
np.set_printoptions(formatter={'int':hex})

from ..generic6502 import lib6502, Generic6502
from ..generic6502 import dtypes as d

import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


debug_frames = False


class Crabapple(Generic6502):
    cpu = "6502"
    name = "crabapple"
    pretty_name = "Crabapple 2+"

    mime_prefix = "application/vnd.apple2"

    def generate_extra_segments(self):
        cpu_offset = self.state_start_offset
        memory_offset = cpu_offset + d.CPU_DTYPE.itemsize
        segments = [
            (cpu_offset, d.CPU_DTYPE.itemsize, 0, "CPU Status"),
            (memory_offset, d.MAIN_MEMORY_SIZE, 0, "Main Memory"),
            (memory_offset + 0x400, 0x400, 0, "Text/Lo-res Page 1"),
            (memory_offset + 0x800, 0x400, 0, "Text/Lo-res Page 2"),
            (memory_offset + 0x2000, 0x2000, 0, "Hi-res Page 1"),
            (memory_offset + 0x4000, 0x2000, 0, "Hi-res Page 2"),
        ]
        self.segments.extend(segments)

    ##### Input routines

    def send_char(self, key_char):
        pass

    def process_key_state(self):
        pass
