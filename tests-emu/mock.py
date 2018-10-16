import sys
sys.path[0:0] = [".."]

import numpy as np
np.set_printoptions(formatter={'int':hex})

from omnivore.emulator_base import EmulatorBase

import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


DUMMY_INPUT_DTYPE = np.dtype([
    ("keychar", np.uint8),
    ("keycode", np.uint8),
])

DUMMY_OUTPUT_DTYPE = np.dtype([
    ("frame_number", np.uint32),
    ("frame_finished", np.uint8),
    ("breakpoint_hit", np.uint8),
    ("unused1", np.uint8),
    ("unused2", np.uint8),
    ("state", np.uint8, 256),
    ("video", np.uint8, 256),
    ("audio", np.uint8, 256),
])

class DummyLowLevel:
    def clear_state_arrays(self, input, output):
        return

    def start_emulator(self, *args, **kwargs):
        return


class DummyEmulator(EmulatorBase):
    cpu = "dummy"
    name = "dummy"
    pretty_name = "Dummy Emulator"

    mime_prefix = ""

    input_array_dtype = DUMMY_INPUT_DTYPE
    output_array_dtype = DUMMY_OUTPUT_DTYPE
    width = 16
    height = 16

    low_level_interface = DummyLowLevel()

    def calc_cpu_data_array(self):
        return None
