import os
import itertools

import numpy as np
import json
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omnivore.arch.disasm import Basic6502Disassembler

from atrcopy import SegmentData, DefaultSegment


class TestCopyPaste(object):
    def setup(self):
        data = np.arange(256, dtype=np.uint8)
        style = np.zeros(256, dtype=np.uint8)
        raw = SegmentData(data, style)
        segment = DefaultSegment(raw, 0)
        self.editor = MockHexEditor(segment=segment)

    def test_metadata(self):
        s = self.editor.segment
        s.set_style_ranges([(10,20),], data=True)
        s.set_style_ranges([(30,40),], user=1)
        s.set_comment([(0,5)], "comment 0-5")
        s.set_comment([(15,16)], "comment 15-16")
        s.set_comment([(18,24)], "comment 18,24")
        s.set_comment([(38,42)], "comment 38,42")
        s.set_comment([(51,55)], "comment 51,55")
        indexes = np.asarray([4,5,8,9,10,11,12,13,28,29,30,31,32,40,41,50,51,52])
        j = self.editor.get_selected_index_metadata(indexes)
        print j
        metadata = json.loads(j)
        style = np.asarray(metadata[0], dtype=np.uint8)
        comments = metadata[1]
        print style
        s1 = s.get_style_at_indexes(indexes)
        assert np.all((s1 - style) == 0)
        print comments

        dest = 100
        last = dest + len(style)
        s.style[dest:last] = style
        assert np.all(s.style[dest:last] - style == 0)
        # for index, comment in comments:
        #     s.set_comment(index, comment)



if __name__ == "__main__":
    t = TestSegment1()
    t.setup()
    t.test_simple()
