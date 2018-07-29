#!/usr/bin/env python
import sys
import ctypes
import time

import numpy as np

import omni8bit
import omni8bit.generic6502.dtypes as d


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
        emu.configure_emulator()
        names = emu.names
        print(names)
        # with open("state.a8", "wb") as fh:
        #     fh.write(emu.state_array)
        num_breaks = 5
        while emu.current_frame_number < 200:
            brk = emu.next_frame()
            if brk:
                if brk.id == 0:
                    # Stepping
                    print(f"step {brk} at {emu.current_cycle_in_frame} cycles into frame {emu.current_frame_number}")
                    time.sleep(.1)
                    num_breaks -= 1
                    if num_breaks <= 0:
                        brk.disable()
                else:
                    print(f"break condition {brk} at {emu.current_cycle_in_frame} cycles into frame {emu.current_frame_number}")
                    time.sleep(.1)
                    num_breaks -= 1
                    if num_breaks <= 0:
                        brk.disable()
                        num_breaks = 10
                        emu.step_into(1)
            else:
                print(f"completed frame {emu.current_frame_number}: {emu.current_cpu_status}")
                # if emu.current_frame_number > 11:
                #     emu.enter_debugger()
                if emu.current_frame_number > 10:
                    emu.debug_video()
                    # emu.debug_state()
                if emu.current_frame_number > 100:
                    emu.keypress('A')
                if emu.current_frame_number == 180:
                    b = emu.create_breakpoint(0xf018)
                if emu.current_frame_number == 190:
                    b = emu.step_into(100)

        print(f"access frame {np.where(emu.memory_access_array > 0)[0]}")
        print(f"read access {np.where(emu.access_type_array & d.ACCESS_TYPE_READ)[0]}")
        print(f"write access{np.where(emu.access_type_array & d.ACCESS_TYPE_WRITE)[0]}")
        print(f"exec access {np.where(emu.access_type_array & d.ACCESS_TYPE_EXECUTE)[0]}")
