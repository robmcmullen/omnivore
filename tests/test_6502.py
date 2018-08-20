import sys
sys.path[0:0] = [".."]

import pytest

import numpy as np
import jsonpickle

import omni8bit


def copynp(state):
    state2 = {}
    for k, v in state.items():
        if isinstance(v, np.ndarray):
            v = v.copy()
        state2[k] = v
    return state2


class Test6502(object):
    emu_name = '6502'

    def setup(self):
        emu_cls = omni8bit.find_emulator(self.emu_name)
        self.emu = emu_cls()
        self.emu.configure_emulator()

    def test_serialize(self):
        emu = self.emu
        while emu.current_frame_number < 50:
            emu.next_frame()
        state1 = copynp(emu.__getstate__())
        cycles1 = emu.cycles_since_power_on
        print(cycles1, state1)
        print(emu.status['cycles_since_power_on'][0])
        while emu.current_frame_number < 100:
            emu.next_frame()
        state2 = copynp(emu.__getstate__())
        cycles2 = emu.cycles_since_power_on
        output2 = emu.output_raw.copy()
        print(cycles2, state2)
        print(emu.status['cycles_since_power_on'][0])

        emu.__setstate__(state1)
        state1a = copynp(emu.__getstate__())
        cycles1a = emu.cycles_since_power_on
        print(cycles1a, state1a)
        print(emu.status['cycles_since_power_on'][0])
        print(emu.output_raw)
        assert(emu.current_frame_number == 50)
        assert(cycles1 == emu.cycles_since_power_on)
        while emu.current_frame_number < 100:
            emu.next_frame()
        state2a = copynp(emu.__getstate__())
        cycles2a = emu.cycles_since_power_on
        output2a = emu.output_raw.copy()
        print(cycles2a, state2a)
        assert(emu.current_frame_number == 100)
        assert(cycles2a == cycles2)
        assert(cycles2a == emu.cycles_since_power_on)

        assert(np.array_equal(output2, output2a))

class TestAtari800(Test6502):
    emu_name = "atari800"
