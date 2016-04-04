import os

import jsonpickle

import numpy as np

from atrcopy import DefaultSegment, SegmentData, IndexedByteSegment


class TestJsonPickle(object):
    def setup(self):
        data = np.arange(2048, dtype=np.uint8)
        self.segment = DefaultSegment(SegmentData(data))

    def test_simple(self):
        print self.segment.byte_bounds_offset(), len(self.segment)
        r2 = self.segment.rawdata[100:400]
        s2 = DefaultSegment(r2)
        print s2.byte_bounds_offset(), len(s2)
        r3 = s2.rawdata[100:200]
        s3 = DefaultSegment(r3)
        print s3.byte_bounds_offset(), len(s3)
        order = list(reversed(range(700, 800)))
        s4 = IndexedByteSegment(self.segment.rawdata, order)
        print s4.byte_bounds_offset(), len(s4)
        
        slist = [s2, s3, s4]
        for s in slist:
            print s
        j = jsonpickle.dumps(slist)
        print j
        
        slist2 = jsonpickle.loads(j)
        print slist2
        for s in slist2:
            s.reconstruct_raw(self.segment.rawdata)
            print s
        
        for orig, rebuilt in zip(slist, slist2):
            print "orig", orig.data
            print "rebuilt", rebuilt.data
            assert np.array_equal(orig[:], rebuilt[:])

if __name__ == "__main__":
    t = TestJsonPickle()
    t.setup()
    t.test_simple()
