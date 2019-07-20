#!/usr/bin/env python
import os
import sys
import ctypes
import time

import numpy as np

import omnivore.emulator
import omnivore.errors as errors
import omnivore.debugger.dtypes as d


if __name__ == "__main__":
    segment = None
    if len(sys.argv) > 1:
        emu_name = sys.argv[1]
    else:
        emu_name = "6502"
    try:
        emu_cls = omnivore.emulator.find_emulator(emu_name)
    except errors.UnknownEmulatorError:
        print(("Unknown emulator: %s" % emu_name))
    else:
        print(("Emulating: %s" % emu_cls.ui_name))
        emu = emu_cls()
        emu.configure_emulator()
        hist = emu.cpu_history
        first_entry_of_frame = 0
        while emu.current_frame_number < 10:
            first_entry_of_frame = hist.next_entry_index
            emu.next_frame()
            print(f"completed frame {emu.current_frame_number}: {emu.current_cpu_status}, history={first_entry_of_frame}")

        restart_number = 0
        frame_number = 2
        state0 = emu.current_restart[frame_number]
        memory0 = emu.main_memory[:]
        print(f"before: {memory0}")

        emu.restore_restart(restart_number, frame_number)

        while emu.current_frame_number < 10:
            first_entry_of_frame = hist.next_entry_index
            emu.next_frame()
            print(f"completed frame {emu.current_frame_number}: {emu.current_cpu_status}, history={first_entry_of_frame}")

        state1 = emu.current_restart[frame_number]
        memory1 = emu.main_memory[:]
        print(f"after: {memory1}")

        memnonzero = np.where(memory0 != 0)[0]
        print(f"memnonzero: {memnonzero}")
        memtest = memory1 - memory0
        membad = np.where(memtest != 0)[0]
        print(f"memtest: {membad}")


        emu.restore_restart_plus(restart_number, frame_number, 1000)
        print(f"partial frame {emu.current_frame_number}: {emu.current_cpu_status}, history={first_entry_of_frame}")
        memory2 = emu.main_memory[:]
        print(f"plus: {memory2}")
        memnonzero = np.where(memory2 != 0)[0]
        print(f"memnonzero: {memnonzero}")
        memtest = memory2 - memory0
        membad = np.where(memtest != 0)[0]
        print(f"memtest: {membad}")
