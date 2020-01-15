#!/usr/bin/env python
import os
import sys
import ctypes
import time

import numpy as np

from omnivore.emulators.generic6502 import lib6502


if __name__ == "__main__":
    emu = lib6502
    emu.init_emulator(None)
    result = emu.next_frame(None)
    print(f"result={result}")
    ops = emu.export_op_history()
    print(f"ops={ops}")
