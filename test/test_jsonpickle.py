from __future__ import print_function
from builtins import zip
from builtins import range
from builtins import object
import os

import pytest
jsonpickle = pytest.importorskip("jsonpickle")

import numpy as np

from atrcopy import DefaultSegment, SegmentData


class TestJsonPickle:
    def setup(self):
        data = np.arange(2048, dtype=np.uint8)
        self.segment = DefaultSegment(SegmentData(data))

    def test_simple(self):
        print(self.segment.byte_bounds_offset(), len(self.segment))
        r2 = self.segment.rawdata[100:400]
        s2 = DefaultSegment(r2)
        print(s2.byte_bounds_offset(), len(s2), s2.__getstate__())
        r3 = s2.rawdata[100:200]
        s3 = DefaultSegment(r3)
        print(s3.byte_bounds_offset(), len(s3), s3.__getstate__())
        order = list(reversed(list(range(700, 800))))
        r4 = self.segment.rawdata.get_indexed(order)
        s4 = DefaultSegment(r4)
        print(s4.byte_bounds_offset(), len(s4), s4.__getstate__())
        
        slist = [s2, s3, s4]
        for s in slist:
            print(s)
        j = jsonpickle.dumps(slist)
        print(j)
        
        slist2 = jsonpickle.loads(j)
        print(slist2)
        for s in slist2:
            s.reconstruct_raw(self.segment.rawdata)
            print(s)
        
        for orig, rebuilt in zip(slist, slist2):
            print("orig", orig.data[:])
            print("rebuilt", rebuilt.data[:])
            assert np.array_equal(orig[:], rebuilt[:])

if __name__ == "__main__":
    t = TestJsonPickle()
    t.setup()
    t.test_simple()
