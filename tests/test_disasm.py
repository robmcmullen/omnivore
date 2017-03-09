import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omni8bit.arch.disasm import *

from atrcopy import SegmentData, DefaultSegment


class TestFastDisasm(object):
    def get_disasm(self):
        return Basic6502Disassembler()

    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/pytest.atr")
        self.editor.load(guess)
        self.disasm = self.get_disasm()
        self.fast = self.disasm.fast

    def test_ranges(self):
        # force the use of the normal disassembler for the other style
        self.disasm.fast.chunk_type_processor[64] = self.disasm.fast.chunk_processor
        self.editor.find_segment("02: robots I")
        s = self.editor.segment
        r = s.get_entire_style_ranges(user=user_bit_mask)
        print r
        assert r == [
        ((0, 497), 0),
        ((497, 524), 1),
        ((524, 602), 0),
        ((602, 690), 1),
        ((690, 1004), 0),
        ((1004, 1024), 1),
        ((1024, 1536), 0),
        ((1536, 1710), 1),
        ((1710, 1792), 0),
        ((1792, 1954), 1),
        ((1954, 2048), 0)]
        info_all = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0)
        #print info_all.instructions[0:20]
        info_sections = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        # for i in range(info_sections.num_instructions):
        #     print info_sections[i].instruction
        assert len(info_all.instructions) == len(info_sections.instructions)
        assert np.all(info_all.index - info_sections.index == 0)

class TestFastDisasmMulti(object):
    def get_disasm(self):
        z = BasicZ80Disassembler()
        parent = Basic6502Disassembler()
        # Use the Z80 processor for style type 64
        parent.fast.chunk_type_processor[1] = z.fast.chunk_processor
        return parent

    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/pytest.atr")
        self.editor.load(guess)
        self.disasm = self.get_disasm()
        self.fast = self.disasm.fast

    def test_ranges(self):
        self.editor.find_segment("boot code at $0800")
        s = self.editor.segment
        r = s.get_entire_style_ranges(user=user_bit_mask)
        print r
        assert r == [((0, 238), 0),
           ((238, 268), 2),
           ((268, 332), 0),
           ((332, 464), 1),
           ((464, 512), 0)]

        info_sections = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        #print info_sections.instructions
        
class TestDisassemblerChange(object):
    def get_disasm(self):
        z = BasicZ80Disassembler()
        parent = Basic6502Disassembler()
        # Use the Z80 processor for style type 1
        parent.fast.chunk_type_processor[1] = z.fast.chunk_processor
        return parent

    def get_break(self, section_break):
        data = np.empty(32, dtype=np.uint8)
        data[0:section_break] = 0x8d
        data[section_break:] = 0xfc
        style = np.empty(32, dtype=np.uint8)
        style[0:section_break] = 0
        style[section_break:] = 1
        raw = SegmentData(data, style)
        segment = DefaultSegment(raw, 0)
        return segment

    def setup(self):
        self.disasm = self.get_disasm()
        self.fast = self.disasm.fast

    def test_simple(self):
        s = self.get_break(8)
        r = s.get_entire_style_ranges(user=user_bit_mask)
        print r
        info = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        inst = info.instructions
        for i in range(info.num_instructions):
            print info[i].instruction

        assert info[1].instruction.startswith("STA")
        assert info[2].instruction.startswith("8d")
        assert info[10].instruction.startswith("CALL")
        assert info[11].instruction.startswith("CALL")
        s = self.get_break(9)
        r = s.get_entire_style_ranges(user=user_bit_mask)
        info = self.fast.get_all(s.rawdata.unindexed_view, s.start_addr, 0, r)
        inst = info.instructions
        for i in range(info.num_instructions):
            print info[i].instruction
        assert info[1].instruction.startswith("STA")
        assert info[2].instruction.startswith("STA")
        assert info[9].instruction.startswith("CALL")
        assert info[10].instruction.startswith("fc")

        
class TestChunkBreak(object):
    def get_disasm(self):
        disasm = Basic6502Disassembler()
        disasm.add_chunk_processor("data", 1)
        disasm.add_chunk_processor("antic_dl", 2)
        disasm.add_chunk_processor("jumpman_level", 3)
        disasm.add_chunk_processor("jumpman_harvest", 4)
        return disasm

    def setup(self):
        self.disasm = self.get_disasm()
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/pytest.atr")
        self.editor.load(guess)

    def test_simple(self):
        self.editor.find_segment("chunk type changes")
        s = self.editor.segment
        r = s.get_entire_style_ranges(user=user_bit_mask)
        print r
        info = self.disasm.disassemble_segment(s)
        inst = info.instructions
        for i in range(info.num_instructions):
            print info[i].instruction

        assert info[0].instruction.startswith("DEX")
        assert info[2].instruction.startswith("RTS")
        assert info[4].instruction == "00"
        assert info[5].instruction.startswith("7070707070;")

    def test_recompile(self):
        self.editor.find_segment("modified boot")
        s = self.editor.segment
        info = self.disasm.disassemble_segment(s)
        disasm = self.disasm.get_disassembled_text()
        with open("%s.s" % s.name, "w") as fh:
            fh.write("\n".join(disasm) + "\n")
        text1 = self.disasm.get_atasm_lst_text()
        with open("%s.omnivore-lst" % s.name, "w") as fh:
            fh.write("\n".join(text1) + "\n")


if __name__ == "__main__":
    t = TestChunkBreak()
    t.setup()
    t.test_recompile()
