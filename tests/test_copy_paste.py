import os
import itertools

import numpy as np
import json
import pytest

from mock import MockHexEditor

from omnivore.utils.file_guess import FileGuess
from omnivore.utils.sortutil import ranges_to_indexes
from omnivore.tasks.hex_edit.commands import PasteCommand

from atrcopy import SegmentData, DefaultSegment


class TestCopyPaste(object):
    def setup(self):
        data = np.arange(256, dtype=np.uint8)
        style = np.zeros(256, dtype=np.uint8)
        raw = SegmentData(data, style)
        s = DefaultSegment(raw, 0)
        s.set_style_ranges([(10,20),], data=True)
        s.set_style_ranges([(30,40),], user=1)
        s.set_comment([(0,5)], "comment 0-5")
        s.set_comment([(15,16)], "comment 15-16")
        s.set_comment([(18,24)], "comment 18,24")
        s.set_comment([(38,42)], "comment 38,42")
        s.set_comment([(51,55)], "comment 51,55")
        self.editor = MockHexEditor(segment=s)

    def test_metadata(self):
        s = self.editor.segment
        indexes = np.asarray([4,5,8,9,10,11,12,13,28,29,30,31,32,40,41,50,51,52])
        j = self.editor.get_selected_index_metadata(indexes)
        style, where_comments, comments = self.editor.restore_selected_index_metadata(j)
        print style
        s1 = s.get_style_at_indexes(indexes)
        assert np.all((s1 - style) == 0)
        print "comments from source", where_comments, comments

        dest = 100
        last = dest + len(style)
        dest_indexes = ranges_to_indexes([(dest, last)])
        print "dest indexes", dest, last, dest_indexes
        assert len(dest_indexes) == len(style)
        s.style[dest_indexes] = style
        assert np.all(s.style[dest_indexes] - style == 0)
        print "dest comment indexes", dest_indexes[where_comments]
        s.set_comments_at_indexes(dest_indexes[where_comments], comments)
        j2 = self.editor.get_selected_index_metadata(dest_indexes)
        style2, where_comments2, comments2 = self.editor.restore_selected_index_metadata(j2)
        print "comments from dest", where_comments2, comments2
        for w, w2 in zip(where_comments, where_comments2):
            assert w == w2
        assert comments == comments2

    def test_command(self):
        s = self.editor.segment
        ranges = [(100,120)]
        dest_indexes = ranges_to_indexes(ranges)
        source_indexes = ranges_to_indexes([(20, 60)])
        common = min(len(dest_indexes), len(source_indexes))
        j = self.editor.get_selected_index_metadata(source_indexes)
        style, where_comments, comments = self.editor.restore_selected_index_metadata(j)
        cmd = PasteCommand(s, ranges, -1, s[source_indexes], source_indexes, style, where_comments, comments)
        cmd.perform(self.editor)

        j2 = self.editor.get_selected_index_metadata(dest_indexes)
        style2, where_comments2, comments2 = json.loads(j2)
        assert np.all(style[0:common] - style2[0:common] == 0)


if __name__ == "__main__":
    t = TestSegment1()
    t.setup()
    t.test_simple()
