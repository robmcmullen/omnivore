#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

import omni8bit


if __name__ == "__main__":
    if len(sys.argv) > 1:
        emu_name = sys.argv[1]
    else:
        emu_name = "6502"
    try:
        emu_cls = omni8bit.find_emulator(emu_name)
    except UnknownEmulatorError:
        print(("Unknown emulator: %s" % emu_name))
    else:
        print(("Emulating: %s" % emu_cls.pretty_name))
        emu = emu_cls()
        emu.begin_emulation()
        names = emu.names
        print(names)
        # with open("state.a8", "wb") as fh:
        #     fh.write(emu.state_array)
        while emu.current_frame_number < 200:
            emu.next_frame()
            print(("run.py frame count =", emu.current_frame_number))
            emu.debug_state()
            # if emu.current_frame_number > 11:
            #     emu.enter_debugger()
            if emu.current_frame_number > 10:
                emu.debug_video()
                # emu.debug_state()
            if emu.current_frame_number > 100:
                emu.keypress('A')
