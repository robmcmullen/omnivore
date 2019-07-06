from __future__ import print_function
from builtins import zip
from builtins import range
from builtins import object
import os

import numpy as np
import pytest

from atrip.container import Container
from atrip.segment import Segment
# from atrip import get_xex, interleave_segments, user_bit_mask, diff_bit_mask
from atrip import errors
from functools import reduce


def get_indexed(segment, num, scale):
    indexes = np.arange(num) * scale
    s = Segment(segment, indexes)
    return s, indexes

# class TestSegment1:
#     def setup(self):
#         self.segments = []
#         for i in range(8):
#             data = np.arange(1024, dtype=np.uint8) * i
#             r = SegmentData(data)
#             self.segments.append(Segment(r, i * 1024))

#     def test_xex(self):
#         items = [
#             [(0, 1, 2), 0],
#             ]
        
#         for indexes, stuff in items:
#             s = [self.segments[i] for i in indexes]
#             s[1].style[0:500] = diff_bit_mask
#             s[1].set_comment_at(0, "comment 0")
#             s[1].set_comment_at(10, "comment 10")
#             s[1].set_comment_at(100, "comment 100")
#             print(list(s[1].iter_comments_in_segment()))
#             with pytest.raises(errors.InvalidBinaryFile):
#                 seg, subseg = get_xex(s, 0xbeef)
#             seg, subseg = get_xex(s)
#             assert tuple(seg.data[0:2]) == (0xff, 0xff)
#             # 2 bytes for the ffff
#             # 4 bytes per segment for start, end address
#             # An extra segment has been inserted for the run address!
#             size = reduce(lambda a, b:a + len(b), subseg, 0)
#             assert len(seg) == 2 + size
#             print(id(s[1]), list(s[1].iter_comments_in_segment()))
#             print(id(subseg[2]), list(subseg[2].iter_comments_in_segment()))
#             for i, c in s[1].iter_comments_in_segment():
#                 assert c == subseg[2].get_comment(i + 4)
#             assert np.all(s[1].style[:] == subseg[2].style[4:])

#     def test_copy(self):
#         for s in self.segments:
#             d = s.rawdata
#             print("orig:", d.data.shape, d.is_indexed, d.data, id(d.data))
#             c = d.copy()
#             print("copy", c.data.shape, c.is_indexed, c.data, id(c.data))
#             assert c.data.shape == s.data.shape
#             assert id(c) != id(s)
#             assert np.all((c.data[:] - s.data[:]) == 0)
#             c.data[0:100] = 1
#             print(d.data)
#             print(c.data)
#             assert not np.all((c.data[:] - s.data[:]) == 0)


class TestIndexed:
    def setup(self):
        data = np.arange(4096, dtype=np.uint8)
        data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        self.container = Container(data)
        self.segment = Segment(self.container, 0, length=len(self.container))

    def test_offsets(self):
        assert np.array_equal(self.segment.container_offset, np.arange(len(self.container)))

    def test_subset(self):
        # get indexed, will result in every 3th byte
        s, indexes = get_indexed(self.segment, 256, 3)
        assert np.array_equal(s.container_offset, indexes)
        for i in range(len(indexes)):
            index_in_source = i * 3
            assert np.array_equal(s.container_offset[i], index_in_source)
            s[i] = 33
            assert s[i] == self.container[index_in_source]
            self.container[index_in_source] = 3
            assert s[i] == self.container[index_in_source]

        # get indexed into indexed, will result in every 9th byte
        s2, indexes2 = get_indexed(s, 64, 3)
        assert np.array_equal(s2.container_offset, indexes2 * 3)
        for i in range(len(indexes2)):
            index_in_source = i * 9
            assert np.array_equal(s2.container_offset[i], index_in_source)
            s2[i] = 99
            assert s2[i] == self.container[index_in_source]
            self.container[index_in_source] = 9
            assert s2[i] == self.container[index_in_source]

    # def test_indexed_sub(self):
    #     base = self.segment
    #     assert not base.rawdata.is_indexed
    #     raw = base.rawdata[512:1536]  # 1024 byte segment
    #     sub = Segment(raw, 512)
        
    #     assert not sub.rawdata.is_indexed
    #     for i in range(len(sub)):
    #         ri = sub.get_raw_index(i)
    #         assert ri == sub.origin + i
    #         assert sub[i] == base[ri]
    #     start, end = sub.byte_bounds_offset()
    #     assert start == 512
    #     assert end == 1536
        
    #     with pytest.raises(IndexError) as e:
    #         # attempt to get indexes to 1024 * 3... Index to big => fail!
    #         s, indexes = get_indexed(sub, 1024, 3)
        
    #     # try with elements up to 256 * 3
    #     s, indexes = get_indexed(sub, 256, 3)
    #     print(sub.data)
    #     print(indexes)
    #     print(s.data[:])
    #     assert s.rawdata.is_indexed
    #     for i in range(len(indexes)):
    #         ri = s.get_raw_index(i)
    #         print(ri, "base[ri]=%d" % base[ri], i, indexes[i], "s[i]=%d" % s[i])
    #         assert ri == sub.origin + indexes[i]
    #         assert s[i] == base[ri]
    #     start, end = s.byte_bounds_offset()
    #     assert start == 0
    #     assert end == len(base)
        
    #     # get indexed into indexed, will result in every 9th byte
    #     s2, indexes2 = get_indexed(s, 64, 3)
    #     assert s2.rawdata.is_indexed
    #     for i in range(len(indexes2)):
    #         assert s2.get_raw_index(i) == sub.origin + indexes2[i] * 3
    #     start, end = s.byte_bounds_offset()
    #     assert start == 0
    #     assert end == len(base)

    # def test_interleave(self):
    #     base = self.segment
    #     r1 = base.rawdata[512:1024]  # 512 byte segment
    #     s1 = Segment(r1, 512)
    #     r2 = base.rawdata[1024:1536]  # 512 byte segment
    #     s2 = Segment(r2, 1024)
        
    #     indexes1 = r1.get_indexes_from_base()
    #     verify1 = np.arange(512, 1024, dtype=np.uint32)
    #     assert np.array_equal(indexes1, verify1)
        
    #     indexes2 = r2.get_indexes_from_base()
    #     verify2 = np.arange(1024, 1536, dtype=np.uint32)
    #     assert np.array_equal(indexes2, verify2)
        
    #     s = interleave_segments([s1, s2], 2)
    #     a = np.empty(len(s1) + len(s2), dtype=np.uint8)
    #     a[0::4] = s1[0::2]
    #     a[1::4] = s1[1::2]
    #     a[2::4] = s2[0::2]
    #     a[3::4] = s2[1::2]
    #     print(list(s[:]))
    #     print(list(a[:]))
    #     print(s.rawdata.order)
    #     assert np.array_equal(s[:], a)
        
    #     s = interleave_segments([s1, s2], 4)
    #     a = np.empty(len(s1) + len(s2), dtype=np.uint8)
    #     a[0::8] = s1[0::4]
    #     a[1::8] = s1[1::4]
    #     a[2::8] = s1[2::4]
    #     a[3::8] = s1[3::4]
    #     a[4::8] = s2[0::4]
    #     a[5::8] = s2[1::4]
    #     a[6::8] = s2[2::4]
    #     a[7::8] = s2[3::4]
    #     assert np.array_equal(s[:], a)

    # def test_interleave_not_multiple(self):
    #     base = self.segment
    #     r1 = base.rawdata[512:1024]  # 512 byte segment
    #     s1 = Segment(r1, 512)
    #     r2 = base.rawdata[1024:1536]  # 512 byte segment
    #     s2 = Segment(r2, 1024)
        
    #     indexes1 = r1.get_indexes_from_base()
    #     verify1 = np.arange(512, 1024, dtype=np.uint32)
    #     assert np.array_equal(indexes1, verify1)
        
    #     indexes2 = r2.get_indexes_from_base()
    #     verify2 = np.arange(1024, 1536, dtype=np.uint32)
    #     assert np.array_equal(indexes2, verify2)
        
    #     s = interleave_segments([s1, s2], 3)

    #     # when interleave size isn't a multiple of the length, the final array
    #     # will reduce the size of the input array to force it to be a multiple.
    #     size = (len(s1) // 3) * 3
    #     assert len(s) == size * 2
    #     a = np.empty(len(s), dtype=np.uint8)
    #     a[0::6] = s1[0:size:3]
    #     a[1::6] = s1[1:size:3]
    #     a[2::6] = s1[2:size:3]
    #     a[3::6] = s2[0:size:3]
    #     a[4::6] = s2[1:size:3]
    #     a[5::6] = s2[2:size:3]
    #     assert np.array_equal(s[:], a)

    # def test_interleave_different_sizes(self):
    #     base = self.segment
    #     r1 = base.rawdata[512:768]  # 256 byte segment
    #     s1 = Segment(r1, 512)
    #     r2 = base.rawdata[1024:1536]  # 512 byte segment
    #     s2 = Segment(r2, 1024)
        
    #     indexes1 = r1.get_indexes_from_base()
    #     verify1 = np.arange(512, 768, dtype=np.uint32)
    #     assert np.array_equal(indexes1, verify1)
        
    #     indexes2 = r2.get_indexes_from_base()
    #     verify2 = np.arange(1024, 1536, dtype=np.uint32)
    #     assert np.array_equal(indexes2, verify2)
        
    #     s = interleave_segments([s1, s2], 3)

    #     # when interleave size isn't a multiple of the length, the final array
    #     # will reduce the size of the input array to force it to be a multiple.
    #     size = (min(len(s1), len(s2)) // 3) * 3
    #     assert size == (256 // 3) * 3
    #     assert len(s) == size * 2
    #     a = np.empty(len(s), dtype=np.uint8)
    #     a[0::6] = s1[0:size:3]
    #     a[1::6] = s1[1:size:3]
    #     a[2::6] = s1[2:size:3]
    #     a[3::6] = s2[0:size:3]
    #     a[4::6] = s2[1:size:3]
    #     a[5::6] = s2[2:size:3]
    #     assert np.array_equal(s[:], a)

    # def test_copy(self):
    #     s, indexes = get_indexed(self.segment, 1024, 3)
    #     c = s.rawdata.copy()
    #     print(c.data.shape, c.is_indexed)
    #     print(id(c.data.np_data), id(s.data.np_data))
    #     assert c.data.shape == s.data.shape
    #     assert id(c) != id(s)
    #     assert np.all((c.data[:] - s.data[:]) == 0)
    #     c.data[0:100] = 1
    #     assert not np.all((c.data[:] - s.data[:]) == 0)


# class TestComments:
#     def setup(self):
#         data = np.ones([4000], dtype=np.uint8)
#         r = SegmentData(data)
#         self.segment = Segment(r, 0)
#         self.sub_segment = Segment(r[2:202], 2)

#     def test_locations(self):
#         s = self.segment
#         s.set_comment([[4,5]], "test1")
#         s.set_comment([[40,50]], "test2")
#         s.set_style_ranges([[2,100]], comment=True)
#         s.set_style_ranges([[200, 299]], data=True)
#         for i in range(1,4):
#             for j in range(1, 4):
#                 # create some with overlapping regions, some without
#                 r = [500*j, 500*j + 200*i + 200]
#                 s.set_style_ranges([r], user=i)
#                 s.set_user_data([r], i, i*10 + j)
#         r = [100, 200]
#         s.set_style_ranges([r], user=4)
#         s.set_user_data([r], 4, 99)
#         r = [3100, 3200]
#         s.set_style_ranges([r], user=4)
#         s.set_user_data([r], 4, 99)

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


# class TestResize:
#     def setup(self):
#         data = np.arange(4096, dtype=np.uint8)
#         data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
#         r = SegmentData(data)
#         self.container = Segment(r, 0)
#         self.container.can_resize = True

#     def test_subset(self):
#         # check to see data a view of some rawdata will be the same when the
#         # rawdata is resized.
#         c = self.container
#         assert not c.rawdata.is_indexed
#         offset = 1000
#         s = Segment(c.rawdata[offset:offset + offset], 0)
#         assert not s.rawdata.is_indexed

#         # Check that the small view has the same data as its parent
#         for i in range(offset):
#             assert s[i] == c[i + offset]

#         # keep a copy of the old raw data of the subset
#         oldraw = s.rawdata.copy()
#         oldid = id(s.rawdata)

#         requested = 8192
#         oldsize, newsize = c.resize(requested)
#         assert newsize == requested
#         s.replace_data(c)  # s should point to the same offset in the resized data
#         assert id(s.rawdata) == oldid  # segment rawdata object should be same
#         assert id(oldraw.order) == id(s.rawdata.order)  # order the same
#         for i in range(offset):  # check values compared to parent
#             assert s[i] == c[i + offset]

#         # check for changes in parent/view reflected so we see that it's
#         # pointing to the same array in memory
#         newbase = c.rawdata
#         newsub = s.rawdata
#         print(c.rawdata.data[offset:offset+offset])
#         print(s.rawdata.data[:])
#         s.rawdata.data[:] = 111
#         print(c.rawdata.data[offset:offset+offset])
#         print(s.rawdata.data[:])
#         for i in range(offset):
#             assert s[i] == c[i + offset]

#     def test_indexed(self):
#         c = self.container
#         assert not c.rawdata.is_indexed
#         s, indexes = get_indexed(self.container, 1024, 3)
#         assert s.rawdata.is_indexed
#         for i in range(len(indexes)):
#             assert s.get_raw_index(i) == indexes[i]
#         requested = 8192
#         oldraw = s.rawdata.copy()
#         oldid = id(s.rawdata)
#         oldsize, newsize = c.resize(requested)
#         assert newsize == requested
#         s.replace_data(c)
#         assert id(s.rawdata) == oldid
#         assert id(oldraw.order) == id(s.rawdata.order)
#         for i in range(len(indexes)):
#             assert s.get_raw_index(i) == indexes[i]
#         newbase = c.rawdata
#         newsub = s.rawdata
#         print(c.rawdata.data)
#         print(s.rawdata.data[:])
#         s.rawdata.data[:] = 111
#         print(c.rawdata.data)
#         print(s.rawdata.data[:])
#         for i in range(len(indexes)):
#             assert c.rawdata.data[indexes[i]] == s.rawdata.data[i]



if __name__ == "__main__":
    t = TestIndexed()
    t.setup()
    t.test_subset()
    # t.test_indexed_sub()
    # t.test_interleave()
    # t = TestSegment1()
    # t.setup()
    # t.test_xex()
    # t.test_copy()
    # t = TestComments()
    # t.setup()
    # t.test_split_data_at_comment()
    # t.test_restore_comments()
    # t = TestResize()
    # t.setup()
    # t.test_subset()
