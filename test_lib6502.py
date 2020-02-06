#!/usr/bin/env python
import os
import sys
import ctypes
import time

import numpy as np

from omnivore.emulators.libemu import Emu6502
from omnivore.debugger.dtypes import CURRENT_STATE_DTYPE, REG_A, REG_X, REG_Y, REG_SP, REG_SR


def show_current_state(s):
    b = s['reg_byte'][0]
    print(f"PC={int(s['pc']):04x} A={b[REG_A]} X={b[REG_X]} Y={b[REG_Y]} SP={b[REG_SP]} SR={b[REG_SR]}")


def show_op_history(ops):
    print(f"malloc size: {int(ops[0])}")
    print(f"frame number: {int(ops[1])}")
    print(f"records: max={int(ops[2])}, count={int(ops[3])}")
    print(f"line lookup: max={int(ops[4])}, count={int(ops[5])}")
    print(f"byte lookup: max={int(ops[6])}, count={int(ops[7])}")
    for i in range(10):
        line = ops[8 + ops[2] + i]
        next_line = ops[8 + ops[2] + i + 1]
        print(f"{i:4}: {line:5}", end="")
        for j in range(line, next_line):
            print(f" {int(ops3[8 + j]):08x}", end="")
        print()


if __name__ == "__main__":
    emu = Emu6502(None)
    emu.cold_start()

    current_state_raw = np.zeros([CURRENT_STATE_DTYPE.itemsize], dtype=np.uint8)
    current_state = current_state_raw.view(dtype=CURRENT_STATE_DTYPE)

    frame0 = emu.export_frame()
    print(f"frame0={frame0}")

    result = emu.next_frame(None, None)
    print(f"result={result}")
    ops = emu.export_op_history()
    print(f"ops={ops}, shape={ops.shape}")
    save = emu.export_frame()
    print(f"saved={save}")

    for i in range(5):
        result = emu.next_frame(None, None)
        print(f"frame {i} result={result}")
        ops = emu.export_op_history()
        print(f"ops={ops}, shape={ops.shape}")

    print(f"restoring from {frame0}")
    emu.import_frame(frame0)
    emu.fill_current_state(current_state)
    show_current_state(current_state)
    result = emu.next_frame(None, None)
    print(f"result={result}")
    ops2 = emu.export_op_history()
    print(f"ops2={ops2}, shape={ops2.shape}")

    print(f"restoring from {frame0}")
    emu.import_frame(frame0)
    emu.fill_current_state(current_state)
    show_current_state(current_state)
    result = emu.next_frame(None, None)
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

    for i in range(5000):
        op = emu.eval_operation(frame0, current_state, ops3, i)
        show_current_state(current_state)
        if op == 0x28:
            print(f"FINISHED WITH FRAME, processed {i} operations")
            break

    show_op_history(ops3)
