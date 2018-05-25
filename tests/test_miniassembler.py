import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omnivore8bit.arch.disasm import *

from atrcopy import SegmentData, DefaultSegment


class TestMiniasm(object):
    def get_disasm(self):
        return Basic6502Disassembler()

    def setup(self):
        self.disasm = self.get_disasm()

    def test_absolute(self):
        commands = [
            ("jmp $fedc", (0x4c, 0xdc, 0xfe)),
            ("lda $fedc", (0xad, 0xdc, 0xfe)),
            ("jsr $fedc", (0x20, 0xdc, 0xfe)),
        ]

        pc = 0x4000
        for text, expected in commands:
            actual = self.disasm.assemble_text(pc, text)
            print(repr(actual))
            assert expected == actual

    def test_pcr(self):
        commands = [
            ("bne $4050", (0xd0, 0x4e)),
            ("beq $3ff0", (0xf0, 0xee)),
        ]

        pc = 0x4000
        for text, expected in commands:
            actual = self.disasm.assemble_text(pc, text)
            print(", ".join(hex(i) for i in actual))
            assert expected == actual



if __name__ == "__main__":
    t = TestMiniasm()
    t.setup()
    t.test_pcr()
