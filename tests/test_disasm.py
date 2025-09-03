import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore_framework.utils.file_guess import FileGuess
from omnivore.arch.disasm import *

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
        r = fast_get_entire_style_ranges(s, user=user_bit_mask, split_comments=[])
        print(r)
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
        info_all = self.fast.get_all(s.rawdata.unindexed_data, s.origin, 0)
        #print info_all.instructions[0:20]
        info_sections = self.fast.get_all(s.rawdata.unindexed_data, s.origin, 0, r)
        # for i in range(info_sections.num_instructions):
        #     print info_sections[i].instruction
        assert len(info_all.instructions) == len(info_sections.instructions)
        assert np.all(info_all.index_to_row - info_sections.index_to_row == 0)

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
        r = fast_get_entire_style_ranges(s, user=user_bit_mask, split_comments=[])
        print(r)
        assert r == [((0, 238), 0),
           ((238, 268), 2),
           ((268, 332), 0),
           ((332, 464), 1),
           ((464, 512), 0)]

        info_sections = self.fast.get_all(s.rawdata.unindexed_data, s.origin, 0, r)
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
        r = fast_get_entire_style_ranges(s, user=user_bit_mask, split_comments=[])
        print(r)
        info = self.fast.get_all(s.rawdata.unindexed_data, s.origin, 0, r)
        inst = info.instructions
        for i in range(info.num_instructions):
            print(info[i].instruction)

        assert info[1].instruction.startswith("STA")
        assert info[2].instruction.startswith("8d")
        assert info[10].instruction.startswith("CALL")
        assert info[11].instruction.startswith("CALL")
        s = self.get_break(9)
        r = fast_get_entire_style_ranges(s, user=user_bit_mask)
        info = self.fast.get_all(s.rawdata.unindexed_data, s.origin, 0, r)
        inst = info.instructions
        for i in range(info.num_instructions):
            print(info[i].instruction)
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
        r = fast_get_entire_style_ranges(s, user=user_bit_mask)
        print(r)
        info = self.disasm.disassemble_segment(s)
        inst = info.instructions
        for i in range(info.num_instructions):
            print(info[i].instruction)

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

    def test_bad(self):
        data = np.frombuffer("\x8dp0L\xaa8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00pppM\x00p\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\x8d\x8d\x06\x16\x8e\r", dtype=np.uint8)
        style = np.empty(len(data), dtype=np.uint8)
        style[0:17] = 0
        style[17:] = 2
        raw = SegmentData(data, style)
        s = DefaultSegment(raw, 0x3bef)
        info = self.disasm.disassemble_segment(s)
        inst = info.instructions
        for i in range(info.num_instructions):
            print(info[i].instruction)
        text = self.disasm.get_disassembled_text()
        print("\n".join(text))

        text = self.disasm.get_atasm_lst_text()
        print("\n".join(text))

def print_r(r):
    print(r)
    print(", ".join("((0x%04x, 0x%04x), 0x%x)" % (i[0][0], i[0][1], i[1]) for i in r))
    print()

class TestSmall(object):
    def get_disasm(self):
        disasm = Basic6502Disassembler()
        disasm.add_chunk_processor("data", 1)
        disasm.add_chunk_processor("antic_dl", 2)
        disasm.add_chunk_processor("jumpman_level", 3)
        disasm.add_chunk_processor("jumpman_harvest", 4)
        return disasm

    def load(self, path, segment="All"):
        guess = FileGuess(path)
        self.editor.load(guess)
        self.editor.find_segment("All")
        return self.editor.segment

    def setup(self):
        self.disasm = self.get_disasm()
        self.editor = MockHexEditor()

    def test_simple(self):
        tests = [
            ("../test_data/style32.dat", {'user': user_bit_mask}, [data_style],
                [((0x0000, 0x000b), 0), ((0x000b, 0x000c), 1), ((0x000c, 0x000d), 1), ((0x000d, 0x000e), 1), ((0x000e, 0x000f), 0), ((0x000f, 0x0012), 1), ((0x0012, 0x0014), 0), ((0x0014, 0x0017), 1), ((0x0017, 0x0018), 0), ((0x0018, 0x001b), 1), ((0x001b, 0x001d), 1), ((0x001d, 0x001e), 1), ((0x001e, 0x001f), 1), ((0x001f, 0x0020), 0x0)]
                ),
            ("../test_data/style32-comment-group.dat", {'user': user_bit_mask}, [data_style], "same as above"
                ),

        ]
        last_expected = None
        for path, kwargs, split_comments, expected in tests:
            if expected == "same as above":
                expected = last_expected
            s = self.load("../test_data/style32.dat")
            r = fast_get_entire_style_ranges(s, user=user_bit_mask, split_comments=[data_style])
            print_r(r)
            print_r(expected)

            assert r == expected
            last_expected = expected


if __name__ == "__main__":
    t = TestSmall()
    t.setup()
    t.test_simple()
