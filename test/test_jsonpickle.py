from __future__ import print_function
from builtins import zip
from builtins import range
from builtins import object
import os

import pytest
jsonpickle = pytest.importorskip("jsonpickle")

import numpy as np

from atrip import Container, Segment


class TestJsonPickle:
    def setup(self):
        data = np.arange(4096, dtype=np.uint8)
        data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        data[::100] = 0x7f
        self.container = Container(data)
        self.container.disasm_type[100:200] = 10
        self.container.disasm_type[200:300] = 30
        self.container.disasm_type[1200:3000] = 10

    def test_simple_container(self):
        j = jsonpickle.dumps(self.container)
        print(j)
        
        c = jsonpickle.loads(j)
        j2 = jsonpickle.dumps(c)
        print(j2)

        assert j == j2

    def test_simple_segment(self):
        s = Segment(self.container)
        j = jsonpickle.dumps(s)
        print(j)
        
        c = jsonpickle.loads(j)
        j2 = jsonpickle.dumps(c)
        print(j2)

        assert j == j2

    def test_ordered_segment(self):
        order = np.arange(200, 500, dtype=np.uint32)
        order[100:200] = np.arange(0, 100, dtype=np.uint32)
        s = Segment(self.container, order)
        j = jsonpickle.dumps(s)
        print(j)
        
        c = jsonpickle.loads(j)
        j2 = jsonpickle.dumps(c)
        print(j2)

        assert j == j2

        assert np.array_equal(s.container_offset, c.container_offset)

if __name__ == "__main__":
    t = TestJsonPickle()
    t.setup()
    # t.test_simple_container()
    # t.test_simple_segment()
    t.test_ordered_segment()
