import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omnivore.arch.disasm import *

from atrcopy import SegmentData, DefaultSegment


class TestFastDisasm(object):
    def get_disasm(self):
        return Basic6502Disassembler()

    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/Jumpman-2016-commented.atr")
        self.editor.load(guess)
        self.disasm = self.get_disasm()
        self.fast = self.disasm.fast

    def test_ranges(self):
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
        info_all = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0)
        #print info_all.instructions[0:20]
        info_sections = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        #print info_sections.instructions[0:20]
        print info_sections.instructions
        assert len(info_all.instructions) == len(info_sections.instructions)
        assert np.all(info_all.index - info_sections.index == 0)

class TestFastDisasmMulti(object):
    def get_disasm(self):
        z = BasicZ80Disassembler()
        parent = Basic6502Disassembler()
        # Use the Z80 processor for style type 64
        parent.fast.chunk_type_processor[64] = z.fast.chunk_processor
        parent.fast.chunk_type_processor[65] = z.fast.chunk_processor
        return parent

    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/Jumpman-2016-commented.atr")
        self.editor.load(guess)
        self.disasm = self.get_disasm()
        self.fast = self.disasm.fast

    def test_ranges(self):
        self.editor.find_segment("boot code at $0800")
        s = self.editor.segment
        r = s.get_entire_style_ranges(data=True, user=1)
        print r
        assert r == [((0, 238), 0),
           ((238, 268), 65),
           ((268, 332), 0),
           ((332, 464), 64),
           ((464, 512), 0)]

        info_sections = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        #print info_sections.instructions
        
class TestChunkBreak(object):
    def get_disasm(self):
        z = BasicZ80Disassembler()
        parent = Basic6502Disassembler()
        # Use the Z80 processor for style type 64
        parent.fast.chunk_type_processor[64] = z.fast.chunk_processor
        parent.fast.chunk_type_processor[65] = z.fast.chunk_processor
        return parent

    def get_break(self, section_break):
        data = np.empty(32, dtype=np.uint8)
        data[0:section_break] = 0x8d
        data[section_break:] = 0xfc
        style = np.empty(32, dtype=np.uint8)
        style[0:section_break] = 0
        style[section_break:] = 64
        raw = SegmentData(data, style)
        segment = DefaultSegment(raw, 0)
        return segment

    def setup(self):
        self.disasm = self.get_disasm()
        self.fast = self.disasm.fast

    def test_simple(self):
        s = self.get_break(8)
        r = s.get_entire_style_ranges(data=True, user=1)
        info_sections = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        print info_sections.instructions

