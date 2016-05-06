import os

import numpy as np

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

if __name__ == "__main__":
    t = TestSegment1()
    t.setup()
    t.test_xex()
