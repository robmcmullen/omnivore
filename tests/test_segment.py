import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omni8bit.arch.disasm import Basic6502Disassembler

from atrcopy import SegmentData, DefaultSegment, user_bit_mask


class TestSegment1(object):
    def setup(self):
        data = np.arange(32, dtype=np.uint8)
        style = np.zeros(32, dtype=np.uint8)
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
        assert r == [((0,10), 64), ((10, 12), 0), ((12, 15), 1), ((15, 32), 0)]


    def test_comments(self):
        s = self.editor.segment
        r = s.get_style_ranges()
        assert r == [(0,32)]
        s.set_style_ranges([(0,10),], user=2)
        s.set_style_ranges([(16,32),], user=1)
        s.set_comment([(5,6),], "comment #1")
        s.set_comment([(8,10),], "comment #2")
        s.set_comment([(12,14),], "comment #3")
        s.set_comment([(15,20),], "comment #4")
        s.set_comment([(22,23),], "comment #5")
        s.set_comment([(26,28),], "comment #6")
        r = s.get_entire_style_ranges(user=user_bit_mask)
        print s.data
        print s.style
        print r
        assert r == [((0, 10), 2), ((10, 16), 0), ((16, 32), 1)]

        r = s.get_entire_style_ranges(user=user_bit_mask, split_comments=[1])
        print s.data
        print s.style
        print r
        assert r == [((0, 10), 2), ((10, 16), 0), ((16, 22), 1), ((22, 26), 1), ((26, 32), 1)]

if __name__ == "__main__":
    t = TestSegment1()
    t.setup()
    t.test_comments()
