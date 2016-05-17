import os

import numpy as np
import pytest

from atrcopy import DefaultSegment, SegmentData, get_xex, interleave_segments


def get_indexed(segment, num, scale):
    indexes = np.arange(num) * scale
    raw = segment.rawdata.get_indexed(indexes)
    s = DefaultSegment(raw, segment.start_addr + indexes[0])
    return s, indexes

class TestSegment1(object):
    def setup(self):
        self.segments = []
        for i in range(8):
            data = np.ones([1024], dtype=np.uint8) * i
            r = SegmentData(data)
            self.segments.append(DefaultSegment(r, i * 1024))

    def test_xex(self):
        items = [
            [(0, 1, 2), 0],
            ]
        
        for indexes, stuff in items:
            s = [self.segments[i] for i in indexes]
            bytes = get_xex(s, 0xbeef)
            assert tuple(bytes[0:2]) == (0xff, 0xff)
            # 2 bytes for the ffff
            # 6 bytes for the last segment run address
            # 4 bytes per segment for start, end address
            size = reduce(lambda a, b:a + 4 + len(b), s, 0)
            assert len(bytes) == 2 + 6 + size


class TestIndexed(object):
    def setup(self):
        data = np.arange(4096, dtype=np.uint8)
        data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        r = SegmentData(data)
        self.segment = DefaultSegment(r, 0)

    def test_indexed(self):
        assert not self.segment.rawdata.is_indexed
        s, indexes = get_indexed(self.segment, 1024, 3)
        assert s.rawdata.is_indexed
        for i in range(len(indexes)):
            assert s.get_raw_index(i) == indexes[i]
        
        # get indexed into indexed, will result in every 9th byte
        s2, indexes2 = get_indexed(s, 256, 3)
        assert s2.rawdata.is_indexed
        for i in range(len(indexes2)):
            assert s2.get_raw_index(i) == indexes2[i] * 3

    def test_indexed_sub(self):
        base = self.segment
        assert not base.rawdata.is_indexed
        raw = base.rawdata[512:1536]  # 1024 byte segment
        sub = DefaultSegment(raw, 512)
        
        assert not sub.rawdata.is_indexed
        for i in range(len(sub)):
            ri = sub.get_raw_index(i)
            assert ri == sub.start_addr + i
            assert sub[i] == base[ri]
        start, end = sub.byte_bounds_offset()
        assert start == 512
        assert end == 1536
        
        with pytest.raises(IndexError) as e:
            # attempt to get indexes to 1024 * 3... Index to big => fail!
            s, indexes = get_indexed(sub, 1024, 3)
        
        # try with elements up to 256 * 3
        s, indexes = get_indexed(sub, 256, 3)
        print sub.data
        print indexes
        print s.data[:]
        assert s.rawdata.is_indexed
        for i in range(len(indexes)):
            ri = s.get_raw_index(i)
            print ri, "base[ri]=%d" % base[ri], i, indexes[i], "s[i]=%d" % s[i]
            assert ri == sub.start_addr + indexes[i]
            assert s[i] == base[ri]
        start, end = s.byte_bounds_offset()
        assert start == 0
        assert end == len(base)
        
        # get indexed into indexed, will result in every 9th byte
        s2, indexes2 = get_indexed(s, 64, 3)
        assert s2.rawdata.is_indexed
        for i in range(len(indexes2)):
            assert s2.get_raw_index(i) == sub.start_addr + indexes2[i] * 3
        start, end = s.byte_bounds_offset()
        assert start == 0
        assert end == len(base)

    def test_interleave(self):
        base = self.segment
        r1 = base.rawdata[512:1024]  # 512 byte segment
        s1 = DefaultSegment(r1, 512)
        r2 = base.rawdata[1024:1536]  # 512 byte segment
        s2 = DefaultSegment(r2, 1024)
        
        indexes1 = r1.get_indexes_from_base()
        verify1 = np.arange(512, 1024, dtype=np.uint32)
        assert np.array_equal(indexes1, verify1)
        
        indexes2 = r2.get_indexes_from_base()
        verify2 = np.arange(1024, 1536, dtype=np.uint32)
        assert np.array_equal(indexes2, verify2)
        
        s = interleave_segments([s1, s2], 2)
        a = np.empty(len(s1) + len(s2), dtype=np.uint8)
        a[0::4] = s1[0::2]
        a[1::4] = s1[1::2]
        a[2::4] = s2[0::2]
        a[3::4] = s2[1::2]
        print list(s[:])
        print list(a[:])
        print s.rawdata.order
        assert np.array_equal(s[:], a)
        
        s = interleave_segments([s1, s2], 4)
        a = np.empty(len(s1) + len(s2), dtype=np.uint8)
        a[0::8] = s1[0::4]
        a[1::8] = s1[1::4]
        a[2::8] = s1[2::4]
        a[3::8] = s1[3::4]
        a[4::8] = s2[0::4]
        a[5::8] = s2[1::4]
        a[6::8] = s2[2::4]
        a[7::8] = s2[3::4]
        assert np.array_equal(s[:], a)
        
        with pytest.raises(ValueError) as e:
            s = interleave_segments([s1, s2], 3)

        r1 = base.rawdata[512:1025]  # 513 byte segment
        s1 = DefaultSegment(r1, 512)
        r2 = base.rawdata[1024:1537]  # 513 byte segment
        s2 = DefaultSegment(r2, 1024)
        s = interleave_segments([s1, s2], 3)
        a = np.empty(len(s1) + len(s2), dtype=np.uint8)
        a[0::6] = s1[0::3]
        a[1::6] = s1[1::3]
        a[2::6] = s1[2::3]
        a[3::6] = s2[0::3]
        a[4::6] = s2[1::3]
        a[5::6] = s2[2::3]
        assert np.array_equal(s[:], a)


if __name__ == "__main__":
    t = TestIndexed()
    t.setup()
    t.test_indexed()
    t.test_indexed_sub()
    t.test_interleave()
