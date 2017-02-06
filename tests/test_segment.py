import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omnivore.arch.disasm import Basic6502Disassembler

from atrcopy import SegmentData, DefaultSegment


class TestSegment1(object):
    def setup(self):
        data = np.arange(16, dtype=np.uint8)
        style = np.zeros(16, dtype=np.uint8)
        raw = SegmentData(data, style)
        segment = DefaultSegment(raw, 0)
        self.editor = MockHexEditor(segment=segment)

    def test_simple(self):
        s = self.editor.segment
        r = s.get_style_ranges()
        assert r == [(0,16)]
        s.set_style_ranges([(0,10),], data=True)
        s.set_style_ranges([(12,15),], user=1)
        r = s.get_style_ranges(data=True)
        print r
        print s.data
        print s.style
        assert r == [(0,10)]
        r = s.get_entire_style_ranges(data=True, user=1)
        assert r == [((0,10), 64), ((10, 12), 0), ((12, 15), 1), ((15, 16), 0)]


if __name__ == "__main__":
    t = TestSegment1()
    t.setup()
    t.test_simple()