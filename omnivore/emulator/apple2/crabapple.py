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
    ui_name = "Crabapple 2+"

    mime_types = set(["application/vnd.apple2.bin"])

    def configure_emulator_defaults(self):
        lib6502.set_a2_emulation_mode(1)

    def generate_save_state_memory_blocks(self):
        cpu_offset = self.state_start_offset
        memory_offset = cpu_offset + d.CPU_DTYPE.itemsize
        segments = [
            (cpu_offset, d.CPU_DTYPE.itemsize, 0, "CPU Status"),
            (memory_offset, d.MAIN_MEMORY_SIZE, 0, "Main Memory"),
            (memory_offset + 0x400, 0x400, 0x400, "Text/Lo-res Page 1"),
            (memory_offset + 0x800, 0x400, 0x800, "Text/Lo-res Page 2"),
            (memory_offset + 0x2000, 0x2000, 0x2000, "Hi-res Page 1"),
            (memory_offset + 0x4000, 0x2000, 0x4000, "Hi-res Page 2"),
        ]
        self.save_state_memory_blocks.extend(segments)
