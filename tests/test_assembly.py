import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore_framework.utils.file_guess import FileGuess

from pyatasm import Assemble
from atrcopy import SegmentData, DefaultSegment


class TestAssemble(object):
    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/reassembly-test.xex")
        self.editor.load(guess)
        print(self.editor.document.segments)
        self.segment = self.editor.document.segments[0][6:6 + 0x125]
        print(self.segment)

    def test_reassemble(self):
        source = "../test_data/reassembly-test.s"
        asm = Assemble(source)
        assert asm is not None
        assert len(asm) == 1
        assert len(asm.segments) == 1
        start, end, source_bytes = asm.segments[0]
        assert len(source_bytes) == len(self.segment)
        print(source_bytes)
        source_data = np.asarray(source_bytes, dtype=np.uint8)
        print(source_data)
        segment_data = np.asarray(self.segment, dtype=np.uint8)
        assert np.all(source_data - segment_data == 0)
