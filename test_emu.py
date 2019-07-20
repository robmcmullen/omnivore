#!/usr/bin/env python
import os
import sys
import ctypes
import time

import numpy as np

import omnivore.emulator
import omnivore.errors as errors
import omnivore.debugger.dtypes as d

class Segment:
    def __init__(self, data, origin):
        self.data = data
        self.origin = origin
        max_size = (1<<16) - origin
        if max_size < len(data):
            self.data = data[0:max_size]

    def __len__(self):
        return len(self.data)

if __name__ == "__main__":
    segment = None
    if len(sys.argv) > 1:
        emu_name = sys.argv[1]
    else:
        emu_name = "6502"
    try:
        if emu_name == "nes":
            emu_name = "6502"
            data = np.fromfile(os.path.join(os.path.dirname(__file__), "lib6502/6502-emu/test/nestest-real-6502.rom"), dtype=np.uint8)
            segment = Segment(data, 0xc000)
        emu_cls = omnivore.emulator.find_emulator(emu_name)
    except errors.UnknownEmulatorError:
        print(("Unknown emulator: %s" % emu_name))
    else:
        print(("Emulating: %s" % emu_cls.ui_name))
        emu = emu_cls()
        emu.configure_emulator()
        if segment is not None:
            emu.stack_pointer = 0xfd
            emu.boot_from_segment(segment, [])
        hist = emu.cpu_history
        # with open("state.a8", "wb") as fh:
        #     fh.write(emu.state_array)
        num_breaks = 5
        first_entry_of_frame = 0
        print(emu.main_memory[0xc000:])
        print(emu.program_counter)
        print(emu.current_cpu_status)
        # if emu_name == "atari800":
        #     b = emu.create_breakpoint(0xf267)
        # else:
        #     b = emu.create_breakpoint(0xf018)
        # print(b)
        while emu.current_frame_number < 10:
            brk = emu.next_frame()
            print(emu.main_memory[0xc000:])
            print(emu.current_cpu_status)
            hist.summary()
            if brk:
                if brk.id == 0:
                    # Stepping
                    print(f"step {brk} at {emu.current_cycle_in_frame} cycles into frame {emu.current_frame_number}")
                    print(emu.current_cpu_status)
                    print(f"history: {first_entry_of_frame} -> {hist.next_entry_index}")
                    current = hist.stringify(hist.next_entry_index-100, 100)
                    print(f"{len(current)}, ")
                    for instruction, result in current:
                        print(instruction, result)
                    print(f"HIT BREAKPOINT: current instruction = {emu.instructions_since_power_on}")
                    time.sleep(1)
                    num_breaks -= 1
                    if num_breaks <= 0:
                        brk.disable()
                        print(f"DISABLING {brk}")
                    else:
                        emu.step_into(1)
                        print(f"STILL ENABLED: {brk}")
                    time.sleep(1)
                else:
                    print(f"break condition {brk} at {emu.current_cycle_in_frame} cycles into frame {emu.current_frame_number}")
                    time.sleep(.1)
                    num_breaks -= 1
                    if num_breaks <= 0:
                        print(f"disabling break condition {brk} at {emu.current_cycle_in_frame} cycles into frame {emu.current_frame_number}")
                        brk.disable()
                        num_breaks = 10
                        emu.step_into(1)
            else:
                print(f"completed frame {emu.current_frame_number}: {emu.current_cpu_status}")
                hist.debug_range(first_entry_of_frame)
                current = hist.stringify(first_entry_of_frame, 100)
                print(first_entry_of_frame, current)
                print(f"{len(current)}, ")
                for instruction, result in current:
                    print(instruction, result)
                first_entry_of_frame = hist.next_entry_index
                if emu.current_frame_number > 10:
                    emu.debug_video()
                    # emu.debug_state()
                if emu.current_frame_number > 100:
                    emu.keypress('A')
                if emu.current_frame_number == 180:
                    b = emu.create_breakpoint(0xf018)
                # if emu.current_frame_number == 190:
                #     b = emu.step_into(100)

        print(f"access frame {np.where(emu.memory_access_array > 0)[0]}")
        print(f"read access {np.where(emu.access_type_array & d.ACCESS_TYPE_READ)[0]}")
        print(f"write access{np.where(emu.access_type_array & d.ACCESS_TYPE_WRITE)[0]}")
        print(f"exec access {np.where(emu.access_type_array & d.ACCESS_TYPE_EXECUTE)[0]}")
