import os

import numpy as np
import pytest

from atrip.memory_map import MemoryMap


def verify_map(memmap, test_data):
    for addr, label, count in test_data:
        item = memmap[addr]
        assert label == item[0]
        assert count == item[1]
        # print(f"tested {addr}, {label}")

class TestMemoryMap:
    def setup(self):
        pass

    @pytest.mark.parametrize(("filename", "rwtest", "rtest", "wtest"), [
            ["../omnivore/templates/atari800.labels", [(0x0012, "RTCLOK", 3), (0xd01a, "COLBK", 1), (0x200, "VDSLST", 2)], [(0xd000, "M0PF", 1), (0xd207, "POT7", 1)], [(0xd000, "HPOSP0", 1), (0xd207, "AUDC4", 1)]],
        ])
    def test_parse_from_file(self, filename, rwtest, rtest, wtest):
        rw, r, w = MemoryMap.from_file(filename)
        if rwtest is not None:
            verify_map(rw, rwtest)
        if rtest is not None:
            verify_map(r, rtest)
        if wtest is not None:
            verify_map(w, wtest)

    @pytest.mark.parametrize(("entries", "truth"), [
            [[(0, "LNFLG"), (1, "NGFLAG"), (2, "CASINI", "w"), (4, "RAMLO", "w"), (0x12, "RTCLOK", "3b")], [(0, "LNFLG", 1), (1, "NGFLAG", 1), (2, "CASINI", 2), (4, "RAMLO", 2), (0x0012, "RTCLOK", 3)]],
        ])
    def test_parse_from_list(self, entries, truth):
        labels = MemoryMap.from_list("Test", entries)
        verify_map(labels, truth)


if __name__ == "__main__":
    t = TestMemoryMap()
    t.setup()
    t.test_parse_from_file("../omnivore/templates/atari800.labels", [(0x0012, "RTCLOK", 3), (0xd01a, "COLBK", 1), (0x200, "VDSLST", 2)], [(0xd000, "M0PF", 1), (0xd207, "POT7", 1)], [(0xd000, "HPOSP0", 1), (0xd207, "AUDC4", 1)])
