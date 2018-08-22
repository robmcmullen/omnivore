import sys
sys.path[0:0] = [".."]
import json

import pytest

import numpy as np

import omni8bit
from omni8bit.history import History

def compare(array1, array2, name="output"):
    diffs = np.where(array1 - array2 != 0)[0]
    print(f"indexes of {name}: {len(diffs)} differences: {diffs}")
    assert(np.array_equal(array1, array2))


class TestHistory(object):
    def setup(self):
        emu_cls = omni8bit.find_emulator('6502')
        self.emu = emu_cls()
        self.emu.configure_emulator()

    def test_keys(self):
        emu = self.emu
        while emu.current_frame_number < 100:
            emu.next_frame()

        h = emu.history
        k = h.keys()
        print(h)
        assert(len(h) == 10)
        assert(k[-1] == 100)

    def test_serialize(self):
        emu = self.emu
        while emu.current_frame_number < 100:
            emu.next_frame()

        h = emu.history
        state = h.serialize_to_dict()
        print(state)
        assert(len(state) == 1)
        assert(len(state['frame_history']) == 10)

        h2 = History()
        h2.restore_from_dict(state)
        assert(len(h2) == 10)
        state = h2.serialize_to_dict()
        print(state)

    def test_serialize_json(self):
        emu = self.emu
        while emu.current_frame_number < 100:
            emu.next_frame()

        h = emu.history
        state = h.serialize_to_text()
        h2 = History()
        h2.restore_from_text(state)
        assert(len(h2) == 10)
        state = h2.serialize_to_text()
        print(state)
        print(len(state))
