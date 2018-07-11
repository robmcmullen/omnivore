import sys
sys.path[0:0] = [".."]

import pytest

from omni8bit import debugger

from mock import DummyEmulator


class TestBreakpoints(object):
    def setup(self):
        self.emu = DummyEmulator()

    def test_create(self):
        b0 = self.emu.create_breakpoint()
        assert b0.id == 0
        b0.address = 0xdada
        assert self.emu.debug_cmd['num_breakpoints'] == 1
        b1 = self.emu.create_breakpoint()
        assert b1.id == 1
        b1.address == 0xdada
        assert self.emu.debug_cmd['num_breakpoints'] == 2

        b0.clear()
        assert self.emu.debug_cmd['num_breakpoints'] == 2
        b2 = self.emu.create_breakpoint()
        assert b2.id == 0
        b2.address = 0xdada

        self.emu.clear_all_breakpoints()
        assert self.emu.debug_cmd['num_breakpoints'] == 0

if __name__ == "__main__":
    t = TestBreakpoints()
    t.setup()
    t.test_create()
