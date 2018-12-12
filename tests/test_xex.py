import os
import itertools

import numpy as np
import pytest

from mock import MockHexEditor

from omnivore_framework.utils.file_guess import FileGuess
from omnivore.document import SegmentedDocument

from atrcopy import SegmentData, DefaultSegment, get_xex


class TestXex(object):
    def setup(self):
        self.editor = MockHexEditor()
        guess = FileGuess("../test_data/air_defense_v18.atr")
        self.editor.load(guess)

    def test_simple(self):
        d = self.editor.document
        print(d, len(d), d.segments)
        for s in d.segments:
            print(s)
        source = []
        code_seg = d.find_segment_by_name("program code")
        runad_seg = d.find_segment_by_name("runad")
        source.append(code_seg)
        source.append(runad_seg)
        main, sub = get_xex(source)
        print(main, sub)
        print(len(code_seg))
        assert len(sub[0]) == len(code_seg) + 4
        assert len(sub[1]) == len(runad_seg) + 4
        print(list(d.container_segment.iter_comments_in_segment()))
        for i, c in code_seg.iter_comments_in_segment():
            print(i, c)
            assert c == sub[0].get_comment(i + 4)

        newdoc = SegmentedDocument.create_from_segments(main, sub)
        d = {}
        newdoc.serialize_extra_to_dict(d)
        print(d)
        for i, c in d['comments']:
            print(i, c)
            assert c == main.get_comment(i)
        self.editor.save("out.air_defense.atr", document=newdoc)



if __name__ == "__main__":
    t = TestXex()
    t.setup()
    t.test_simple()
