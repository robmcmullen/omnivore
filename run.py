#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

import omni8bit.atari800 as a8
akey = a8.akey

from omni8bit.atari800.save_state_parser import parse_state


if __name__ == "__main__":
    emu = a8.Atari800()
    emu.begin_emulation()
    names = emu.names
    print(names)
    # with open("state.a8", "wb") as fh:
    #     fh.write(emu.state_array)
    while emu.output['frame_number'] < 20:
        emu.next_frame()
        print "run.py frame count =", emu.output['frame_number']
        if emu.output['frame_number'] > 11:
            emu.enter_debugger()
        elif emu.output['frame_number'] > 10:
            emu.debug_video()
            a, p, sp, x, y, _, pc = emu.cpu_state
            print("A=%02x X=%02x Y=%02x SP=%02x FLAGS=%02x PC=%04x" % (a, x, y, sp, p, pc))
            # emu.debug_state()
        if emu.output['frame_number'] > 100:
            emu.input['keychar'] = ord('A')
