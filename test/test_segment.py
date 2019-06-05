from __future__ import print_function
from builtins import zip
from builtins import range
from builtins import object
import os

import numpy as np
import pytest

from atrip.container import Container
from atrip.segment import Segment
import atrip.style_bits as style_bits
import atrip.errors as errors
from atrip.utils import collapse_values, restore_values
from functools import reduce



class TestSegment:
    def setup(self):
        data = np.arange(4096, dtype=np.uint8)
        data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        data[::100] = 0x7f
        self.container = Container(data)
        self.segment = Segment(self.container)
        index_by_100 = np.arange(40, dtype=np.int32) * 100
        self.seg100 = Segment(self.segment, index_by_100)
        self.seg1000 = Segment(self.seg100, [0,10,20,30])

    def samples(self):
        assert self.segment[100] == 0x7f
        assert self.container.data[100] == self.segment[100]
        assert self.segment[100] == self.seg100[1]

        self.segment[100] = 0xff
        assert self.segment[100] == 0xff
        assert self.container.data[100] == self.segment[100]
        assert self.segment[100] == self.seg100[1]

    def test_slice(self):
        self.segment[10:30] = 55
        assert self.segment[20] == 55

        self.seg100[0:11] = np.arange(200, 211)
        assert self.seg100[0] == 200
        assert self.seg1000[0] == 200
        assert self.segment[0] == 200

        assert self.seg100[1] == 201
        assert self.segment[100] == 201

        assert self.seg100[2] == 202
        assert self.segment[200] == 202

        assert self.seg100[10] == 210
        assert self.seg1000[1] == 210
        assert self.segment[1000] == 210

    def test_reverse_offset(self):
        """Test mapping from container element to element in Segment"""
        r1000 = self.seg1000.reverse_offset
        assert r1000[0] == 0
        assert np.all(r1000[1:1000] == -1)
        assert r1000[1000] == 1
        assert r1000[2000] == 2
        assert r1000[3000] == 3

    def test_comments(self):
        s = self.segment
        s100 = self.seg100
        s1000 = self.seg1000
        s.set_comment_at(4, "test4")
        s.set_comment_at(100, "test100")
        s.set_comment_at(400, "test400")
        s.set_comment_at(1000, "test1000")

        assert s.get_comment_at(4) == "test4"
        assert s.style[4] & style_bits.comment_bit_mask
        assert s.get_comment_at(100) == "test100"
        assert s.style[100] & style_bits.comment_bit_mask
        assert s.get_comment_at(400) == "test400"
        assert s.style[400] & style_bits.comment_bit_mask
        assert s.get_comment_at(1000) == "test1000"
        assert s.style[1000] & style_bits.comment_bit_mask

        assert s100.get_comment_at(1) == "test100"
        assert s100.style[1] & style_bits.comment_bit_mask
        assert s100.get_comment_at(4) == "test400"
        assert s100.style[4] & style_bits.comment_bit_mask
        assert s100.get_comment_at(10) == "test1000"
        assert s100.style[10] & style_bits.comment_bit_mask
        assert s1000.get_comment_at(1) == "test1000"
        assert s1000.style[1] & style_bits.comment_bit_mask

        s100.set_comment_at(4, "new400")
        s100.set_comment_at(10, "new1000")
        s1000.set_comment_at(2, "new2000")

        assert s.get_comment_at(400) == "new400"
        assert s.get_comment_at(1000) == "new1000"
        assert s.get_comment_at(2000) == "new2000"
        assert s100.get_comment_at(10) == "new1000"
        assert s100.get_comment_at(20) == "new2000"

        s.set_comment_at(150, "test150")
        s100.clear_comment_ranges([[1,5]])
        assert s.get_comment_at(100) == ""
        assert s.style[100] & style_bits.comment_bit_mask == 0
        assert s.get_comment_at(150) == "test150"
        assert s.style[150] & style_bits.comment_bit_mask
        assert s.get_comment_at(400) == ""
        assert s.style[400] & style_bits.comment_bit_mask == 0
        assert s.get_comment_at(1000) == "new1000"
        assert s.style[1000] & style_bits.comment_bit_mask

    def test_style(self):
        s = self.segment
        s100 = self.seg100
        s1000 = self.seg1000
        s.set_style_ranges([[200, 4000]], selected=True)
        s.set_style_ranges([[1200, 3000]], match=True)
        assert s.style[0] == 0
        assert s100.style[1] == 0
        assert s100.style[10] == style_bits.selected_bit_mask
        assert s100.style[20] == style_bits.selected_bit_mask | style_bits.match_bit_mask
        assert s1000.style[0] == 0
        assert s1000.style[1] == s100.style[10]
        assert s1000.style[2] == s100.style[20]

    def test_metadata(self):
        s = self.segment
        s.set_style_ranges([[200, 400]], selected=True)
        s.set_comment_at(190, "test190")
        s.set_comment_at(210, "test210")
        s.set_comment_at(230, "test230")
        indexes = np.arange(180,220)
        m = s.calc_selected_index_metadata(indexes)
        print(m)
        e = s.encode_selected_index_metadata(*m)

        r = s.restore_selected_index_metadata(e)
        print(r)
        assert r[0].tolist() == m[0].tolist()
        assert r[1].tolist() == m[1].tolist()
        assert r[2] == m[2]

    def test_disasm_type(self):
        s = self.segment
        s100 = self.seg100
        s1000 = self.seg1000
        s.set_disasm_ranges([[200, 4000]], 2)
        s.set_disasm_ranges([[1200, 3000]], 50)
        assert s.disasm_type[0] == 128
        assert s100.disasm_type[1] == 128
        assert s100.disasm_type[10] == 2
        assert s100.disasm_type[20] == 50
        assert s1000.disasm_type[0] == 128
        assert s1000.disasm_type[1] == s100.disasm_type[10]
        assert s1000.disasm_type[2] == s100.disasm_type[20]

        c = s.container
        assert c.disasm_type[2000] == 50

        ranges = collapse_values(c.disasm_type)
        assert ranges == [[128, 0, 200], [2, 200, 1200], [50, 1200, 3000], [2, 3000, 4000], [128, 4000, 4096]]

        c.disasm_type[:] = 0
        assert c.disasm_type[2000] == 0

        restore_values(c.disasm_type, ranges)
        assert s.disasm_type[0] == 128
        assert s100.disasm_type[1] == 128
        assert s100.disasm_type[10] == 2
        assert s100.disasm_type[20] == 50
        assert s1000.disasm_type[0] == 128
        assert s1000.disasm_type[1] == s100.disasm_type[10]
        assert s1000.disasm_type[2] == s100.disasm_type[20]
        assert c.disasm_type[2000] == 50

        r2 = collapse_values(c.disasm_type)
        assert ranges == r2

#         s2 = self.sub_segment
#         print(len(s2))
#         copy = s2.get_comment_locations()
#         print(copy)
#         # comments at 4 and 40 in the original means 2 and 38 in the copy
#         orig = s.get_comment_locations()
#         assert copy[2] == orig[4]
#         assert copy[28] == orig[38]

#     def test_split_data_at_comment(self):
#         s = self.segment
#         s.set_style_ranges([[0,1000]], data=True)
#         for i in range(0, len(s), 25):
#             s.set_comment([[i,i+1]], "comment at %d" % i)

#         s2 = self.sub_segment
#         print(len(s2))
#         copy = s2.get_comment_locations()
#         print(copy)
#         # comments at 4 and 40 in the original means 2 and 38 in the copy
#         orig = s.get_comment_locations()
#         print(orig[0:200])
#         assert copy[2] == orig[4]
#         assert copy[28] == orig[38]

#         r = s2.get_entire_style_ranges([1], user=True)
#         print(r)
#         assert r == [((0, 23), 1), ((23, 48), 1), ((48, 73), 1), ((73, 98), 1), ((98, 123), 1), ((123, 148), 1), ((148, 173), 1), ((173, 198), 1), ((198, 200), 1)]

#     def test_split_data_at_comment2(self):
#         s = self.segment
#         start = 0
#         i = 0
#         for end in range(40, 1000, 40):
#             s.set_style_ranges([[start, end]], user=i)
#             start = end
#             i = (i + 1) % 8
#         for i in range(0, len(s), 25):
#             s.set_comment([[i,i+1]], "comment at %d" % i)

#         s2 = self.sub_segment
#         print(len(s2))
#         copy = s2.get_comment_locations()
#         print(copy)
#         # comments at 4 and 40 in the original means 2 and 38 in the copy
#         orig = s.get_comment_locations()
#         print(orig[0:200])
#         assert copy[2] == orig[4]
#         assert copy[28] == orig[38]

#         r = s2.get_entire_style_ranges([1], user=user_bit_mask)
#         print(r)
#         assert r == [((0, 38), 0), ((38, 48), 1), ((48, 73), 1), ((73, 78), 1), ((78, 118), 2), ((118, 158), 3), ((158, 198), 4), ((198, 200), 5)]

#     def test_restore_comments(self):
#         s = self.segment
#         s.set_style_ranges([[0,1000]], data=True)
#         for i in range(0, len(s), 5):
#             s.set_comment([[i,i+1]], "comment at %d" % i)

#         s1 = self.segment
#         print(len(s1))
#         indexes = [7,12]
#         r = s1.get_comment_restore_data([indexes])
#         print(r)
#         # force clear comments
#         s1.rawdata.extra.comments = {}
#         s1.style[indexes[0]:indexes[1]] = 0
#         r0 = s1.get_comment_restore_data([indexes])
#         print(r0)
#         for start, end, style, items in r0:
#             print(style)
#             assert np.all(style == 0)
#             for rawindex, comment in list(items.values()):
#                 assert not comment
#         s1.restore_comments(r)
#         r1 = s1.get_comment_restore_data([indexes])
#         print(r1)
#         for item1, item2 in zip(r, r1):
#             print(item1)
#             print(item2)
#             for a1, a2 in zip(item1, item2):
#                 print(a1, a2)
#                 if hasattr(a1, "shape"):
#                     assert np.all(a1 - a2 == 0)
#                 else:
#                     assert a1 == a2

#         s2 = self.sub_segment
#         print(len(s2))
#         indexes = [5,10]
#         r = s2.get_comment_restore_data([indexes])
#         print(r)
#         # force clear comments
#         s2.rawdata.extra.comments = {}
#         s2.style[indexes[0]:indexes[1]] = 0
#         r0 = s2.get_comment_restore_data([indexes])
#         print(r0)
#         for start, end, style, items in r0:
#             print(style)
#             assert np.all(style == 0)
#             for rawindex, comment in list(items.values()):
#                 assert not comment
#         s2.restore_comments(r)
#         r2 = s2.get_comment_restore_data([indexes])
#         print(r2)
#         for item1, item2 in zip(r, r2):
#             print(item1)
#             print(item2)
#             for a1, a2 in zip(item1, item2):
#                 print(a1, a2)
#                 if hasattr(a1, "shape"):
#                     assert np.all(a1 - a2 == 0)
#                 else:
#                     assert a1 == a2

#         for item1, item2 in zip(r1, r2):
#             print(item1)
#             print(item2)
#             # indexes won't be the same, but rawindexes and comments will
#             assert np.all(item1[2] - item2[2] == 0)
#             assert set(item1[3].values()) == set(item2[3].values())




if __name__ == "__main__":
    t = TestSegment()
    t.setup()
    t.test_metadata()
#     # t.test_indexed()
#     # t.test_indexed_sub()
#     # t.test_interleave()
#     # t = TestSegment1()
#     # t.setup()
#     # t.test_xex()
#     # t.test_copy()
#     # t = TestComments()
#     # t.setup()
#     # t.test_split_data_at_comment()
#     # t.test_restore_comments()
#     t = TestResize()
#     t.setup()
#     t.test_subset()
