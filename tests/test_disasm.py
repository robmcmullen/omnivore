import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omnivore.arch.disasm import Basic6502Disassembler

from atrcopy import SegmentData, DefaultSegment


class TestFastDisasm(object):
    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/Jumpman-2016-commented.atr")
        self.editor.load(guess)
        self.disasm = Basic6502Disassembler()
        self.fast = self.disasm.fast

    def test_simple(self):
        self.editor.find_segment("02: robots I")
        s = self.editor.segment
        r = s.get_entire_style_ranges(data=True, user=1)
        assert r == [
        ((0, 84), 64),
        ((84, 497), 0),
        ((497, 524), 64),
        ((524, 602), 0),
        ((602, 690), 64),
        ((690, 1004), 0),
        ((1004, 1024), 64),
        ((1024, 1536), 0),
        ((1536, 1710), 64),
        ((1710, 1792), 0),
        ((1792, 1954), 64),
        ((1954, 2048), 0)]
        info = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0)
        for line in info.instructions:
            print line
