import sys
sys.path[0:0] = [".."]

import pytest

from omnivore import debugger

from mock import DummyEmulator


class TestBreakpoints(object):
    def setup(self):
        self.emu = DummyEmulator()
        self.emu.clear_all_breakpoints()

    def test_create(self):
        b0 = self.emu.create_breakpoint(0xdada)
        print(b0)
        assert b0.id == 1
        assert self.emu.debug_cmd['num_breakpoints'] == 2
        b1 = self.emu.create_breakpoint(0xdada)
        print(b1)
        assert b1.id == 2
        assert self.emu.debug_cmd['num_breakpoints'] == 3

        b0.clear()
        assert self.emu.debug_cmd['num_breakpoints'] == 3
        b2 = self.emu.create_breakpoint(0xdada)
        assert b2.id == 1

        self.emu.clear_all_breakpoints()
        assert self.emu.debug_cmd['num_breakpoints'] == 0

if __name__ == "__main__":
    t = TestBreakpoints()
    t.setup()
    t.test_create()
