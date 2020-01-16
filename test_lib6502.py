#!/usr/bin/env python
import os
import sys
import ctypes
import time

import numpy as np

from omnivore.emulators.generic6502 import lib6502
from omnivore.debugger.dtypes import CURRENT_STATE_DTYPE, REG_A, REG_X, REG_Y, REG_SP, REG_SR


def show_current_state(s):
    b = s['reg_byte'][0]
    print(f"PC={s['pc']} A={b[REG_A]} X={b[REG_X]} Y={b[REG_Y]} SP={b[REG_SP]} SR={b[REG_SR]}")

if __name__ == "__main__":
    emu = lib6502
    emu.init_emulator(None)
    emu.cold_start()

    current_state_raw = np.zeros([CURRENT_STATE_DTYPE.itemsize], dtype=np.uint8)
    current_state = current_state_raw.view(dtype=CURRENT_STATE_DTYPE)

    frame0 = emu.export_frame()
    print(f"frame0={frame0}")

    result = emu.next_frame(None)
    print(f"result={result}")
    ops = emu.export_op_history()
    print(f"ops={ops}, shape={ops.shape}")
    save = emu.export_frame()
    print(f"saved={save}")

    for i in range(5):
        result = emu.next_frame(None)
        print(f"frame {i} result={result}")
        ops = emu.export_op_history()
        print(f"ops={ops}, shape={ops.shape}")

    print(f"restoring from {frame0}")
    emu.import_frame(frame0)
    emu.fill_current_state(current_state)
    show_current_state(current_state)
    result = emu.next_frame(None)
    print(f"result={result}")
    ops2 = emu.export_op_history()
    print(f"ops2={ops2}, shape={ops2.shape}")

    print(f"restoring from {frame0}")
    emu.import_frame(frame0)
    emu.fill_current_state(current_state)
    show_current_state(current_state)
    result = emu.next_frame(None)
    print(f"result={result}")
    ops3 = emu.export_op_history()
    print(f"ops3={ops3}, shape={ops2.shape}")

    print(ops)
    print(ops2)
    print(ops3)
    print(np.array_equal(ops2, ops3))

    # display individual instructions
    emu.import_frame(frame0)
    emu.fill_current_state(current_state)
    show_current_state(current_state)

    for i in range(50):
        emu.eval_operation(frame0, current_state, ops3, i)
        show_current_state(current_state)
