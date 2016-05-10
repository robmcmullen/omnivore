import os

import numpy as np
import pytest

from atrcopy import DefaultSegment, SegmentData, get_xex


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

    def get_indexed(self, segment, num, scale):
        indexes = np.arange(num) * scale
        raw = segment.rawdata.get_indexed(indexes)
        s = DefaultSegment(raw, segment.start_addr + indexes[0])
        return s, indexes

    def test_indexed(self):
        assert not self.segment.rawdata.is_indexed
        s, indexes = self.get_indexed(self.segment, 1024, 3)
        assert s.rawdata.is_indexed
        for i in range(len(indexes)):
            assert s.get_raw_index(i) == indexes[i]
        
        # get indexed into indexed, will result in every 9th byte
        s2, indexes2 = self.get_indexed(s, 256, 3)
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
            s, indexes = self.get_indexed(sub, 1024, 3)
        
        # try with elements up to 256 * 3
        s, indexes = self.get_indexed(sub, 256, 3)
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
        s2, indexes2 = self.get_indexed(s, 64, 3)
        assert s2.rawdata.is_indexed
        for i in range(len(indexes2)):
            assert s2.get_raw_index(i) == sub.start_addr + indexes2[i] * 3
        start, end = s.byte_bounds_offset()
        assert start == 0
        assert end == len(base)


if __name__ == "__main__":
    t = TestIndexed()
    t.setup()
    t.test_indexed()
    t.test_indexed_sub()
