import os

import numpy as np
import pytest
import jsonpickle

from atrip.collection import Collection
from atrip.segment import Segment
import atrip.errors as errors



class TestCollection:
    def test_serialize(self):
        filename = "dos_sd_test1.atr"
        pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
        data = np.fromfile(pathname, dtype=np.uint8)
        c = Collection(pathname, data)
        s = {}
        c.serialize_session(s)
        print(s)

        j = jsonpickle.dumps(s)
        print(j)
        
        sprime = jsonpickle.loads(j)
        jprime = jsonpickle.dumps(sprime)
        print(jprime)

        assert j == jprime

        c2 = Collection(pathname, data, sprime)
        s2 = {}
        c2.serialize_session(s2)
        j2 = jsonpickle.dumps(s2)
        assert j == j2



if __name__ == "__main__":
    t = TestCollection()
    t.test_serialize()
