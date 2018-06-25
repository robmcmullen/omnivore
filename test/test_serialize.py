from __future__ import print_function
from builtins import range
from builtins import object
from builtins import str
import os

import numpy as np
import pytest

from atrcopy import DefaultSegment, SegmentData, get_xex, interleave_segments


class TestSegment:
    def setup(self):
        data = np.ones([4000], dtype=np.uint8)
        r = SegmentData(data)
        self.segment = DefaultSegment(r, 0)

    def test_getstate(self):
        state = self.segment.__getstate__()
        for k, v in state.items():
            print("k=%s v=%s type=%s" % (k, v, type(v)))
        byte_type = type(str(u'  ').encode('utf-8'))  # py2 and py3
        try:
            u = unicode(" ")
        except:
            u = str(" ")
        assert type(state['uuid']) == type(u)

    def test_extra(self):
        s = self.segment
        s.set_comment([[4,5]], "test1")
        s.set_comment([[40,50]], "test2")
        s.set_style_ranges([[2,100]], comment=True)
        s.set_style_ranges([[200, 299]], data=True)
        for i in range(1,4):
            for j in range(1, 4):
                # create some with overlapping regions, some without
                r = [500*j, 500*j + 200*i + 200]
                s.set_style_ranges([r], user=i)
                s.set_user_data([r], i, i*10 + j)
        r = [100, 200]
        s.set_style_ranges([r], user=4)
        s.set_user_data([r], 4, 99)
        r = [3100, 3200]
        s.set_style_ranges([r], user=4)
        s.set_user_data([r], 4, 99)

        out = dict()
        s.serialize_extra_to_dict(out)
        print("saved", out)

        data = np.ones([4000], dtype=np.uint8)
        r = SegmentData(data)
        s2 = DefaultSegment(r, 0)
        s2.restore_extra_from_dict(out)
        out2 = dict()
        s2.serialize_extra_to_dict(out2)
        print("loaded", out2)
        assert out == out2


if __name__ == "__main__":
    t = TestSegment()
    t.setup()
    t.test_getstate()
