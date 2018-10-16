import sys
sys.path[0:0] = [".."]
import json

import pytest

import numpy as np

import omnivore


def compare(array1, array2, name="output"):
    diffs = np.where(array1 - array2 != 0)[0]
    print(f"indexes of {name}: {len(diffs)} differences: {diffs}")
    assert(np.array_equal(array1, array2))


class Test6502(object):
    emu_name = '6502'

    def setup(self):
        emu_cls = omnivore.find_emulator(self.emu_name)
        self.emu = emu_cls()
        self.emu.configure_emulator()

    def test_save_state(self):
        emu = self.emu
        state = emu.calc_current_state()
        diffs = np.where(state !=0)[0]
        print(f"diff values: {state[diffs]}\n{diffs}")
        # assert(len(diffs) == 0)
        while emu.current_frame_number < 50:
            emu.next_frame()
        state1 = emu.calc_current_state()
        cycles1 = emu.cycles_since_power_on
        print(cycles1, state1)
        print(emu.status['cycles_since_power_on'][0])
        while emu.current_frame_number < 100:
            emu.next_frame()
        state2 = emu.calc_current_state()
        cycles2 = emu.cycles_since_power_on
        print(cycles2, state2)
        print(emu.status['cycles_since_power_on'][0])

        emu.restore_state(state1)
        state1a = emu.calc_current_state()
        cycles1a = emu.cycles_since_power_on
        print(cycles1a, state1a)
        print(emu.status['cycles_since_power_on'][0])
        print(emu.output_raw)
        assert(emu.current_frame_number == 50)
        assert(cycles1 == emu.cycles_since_power_on)
        while emu.current_frame_number < 100:
            emu.next_frame()
        state2a = emu.calc_current_state()
        cycles2a = emu.cycles_since_power_on
        print(cycles2a, state2a)
        assert(emu.current_frame_number == 100)
        assert(cycles2a == cycles2)
        assert(cycles2a == emu.cycles_since_power_on)

        diffs = np.where(state2a - state2 != 0)[0]
        print(f"indexes of differences: {diffs}")

        assert(np.array_equal(state2, state2a))

    def test_serialize(self):
        emu = self.emu
        # assert(len(np.where(emu.calc_current_state() !=0)[0]) == 0)
        while emu.current_frame_number < 50:
            emu.next_frame()
        output0 = emu.calc_current_state()
        state1 = emu.serialize_to_dict()
        emu.restore_from_dict(state1)
        output0a = emu.calc_current_state()
        compare(output0, output0a, 'output0 - output0a after setstate')

        cycles1 = emu.cycles_since_power_on
        output1 = emu.calc_current_state()
        compare(state1['output_raw'], output1, 'state1 - output1')
        print(cycles1, state1)
        print(emu.status['cycles_since_power_on'][0])
        while emu.current_frame_number < 100:
            emu.next_frame()
        state2 = emu.serialize_to_dict()
        cycles2 = emu.cycles_since_power_on
        output2 = emu.calc_current_state()
        print(cycles2, state2)
        print(emu.status['cycles_since_power_on'][0])
        compare(state1['output_raw'], output1, 'state1 - output1 before setstate')

        emu.restore_from_dict(state1)
        state1a = emu.serialize_to_dict()
        cycles1a = emu.cycles_since_power_on
        output1a = emu.calc_current_state()
        compare(state1['output_raw'], output1, 'state1 - output1 after setstate')
        compare(state1a['output_raw'], state1['output_raw'], 'state1 - state1a')
        compare(state1['output_raw'], output1a, 'state1 - output1a')
        compare(state1a['output_raw'], output1a, 'state1a - output1a')
        compare(state1a['output_raw'], output1, 'state1a - output1')
        print(cycles1a, state1a)
        print(emu.status['cycles_since_power_on'][0])
        print(output1a)
        assert(emu.current_frame_number == 50)
        assert(cycles1 == emu.cycles_since_power_on)
        compare(output1, output1a, 'output1 - output1a')

        while emu.current_frame_number < 100:
            emu.next_frame()
        state2a = emu.serialize_to_dict()
        cycles2a = emu.cycles_since_power_on
        output2a = emu.calc_current_state()
        print(cycles2a, state2a)
        assert(emu.current_frame_number == 100)
        assert(cycles2a == cycles2)
        assert(cycles2a == emu.cycles_since_power_on)
        compare(output2, output2a)

    def test_serialize_json(self):
        emu = self.emu
        while emu.current_frame_number < 50:
            emu.next_frame()
        state1_encoded = emu.serialize_to_text()
        print(state1_encoded)
        cycles1 = emu.cycles_since_power_on
        output1 = emu.calc_current_state()

        while emu.current_frame_number < 100:
            emu.next_frame()
        cycles2 = emu.cycles_since_power_on
        output2 = emu.calc_current_state()

        # state1_restored = json.loads(encoded)
        emu.restore_from_text(state1_encoded)
        cycles1a = emu.cycles_since_power_on
        output1a = emu.calc_current_state()

        print(output1a)
        assert(emu.current_frame_number == 50)
        assert(cycles1 == emu.cycles_since_power_on)
        compare(output1, output1a, 'output1 - output1a')

        while emu.current_frame_number < 100:
            emu.next_frame()
        state2a = emu.serialize_to_dict()
        cycles2a = emu.cycles_since_power_on
        output2a = emu.calc_current_state()
        print(cycles2a, state2a)
        assert(emu.current_frame_number == 100)
        assert(cycles2a == cycles2)
        assert(cycles2a == emu.cycles_since_power_on)
        compare(output2, output2a)

class TestAtari800(Test6502):
    emu_name = "atari800"
    emu = omnivore.find_emulator(emu_name)()

    def test_coldstart(self):
        emu = self.__class__.emu
        emu.configure_emulator()
        print(emu.current_cpu_status)
        print(emu.current_antic_status)
        emu.configure_emulator()
        print(emu.current_cpu_status)
        print(emu.current_antic_status)
        emu.audio_array[:] = 0
        state = emu.calc_current_state()
        emu.configure_emulator()
        print(emu.current_cpu_status)
        print(emu.current_antic_status)
        emu.audio_array[:] = 0
        state2 = emu.calc_current_state()
        print(emu.save_state_memory_blocks)
        diffs = np.where(state - state2 != 0)[0]
        print(f"diff values: {state[diffs]}\n{state2[diffs]}\n{diffs}")

        from omnivore.atari800.save_state_parser import parse_state
        s = parse_state(state2[emu.state_start_offset:], emu.state_start_offset)
        print(s)

        assert(len(diffs) == 0)
        assert(np.array_equal(state, state2))
