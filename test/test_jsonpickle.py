import os

import pytest
jsonpickle = pytest.importorskip("jsonpickle")
jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)

import numpy as np

from atrip import Container, Segment
from atrip.container import guess_container, load


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

    def test_sparse_segment(self):
        offsets = np.arange(40, dtype=np.int32) * 100
        offsets[10:20] = np.arange(70, 80, dtype=np.uint32)
        s = Segment(self.container, offsets)
        j = jsonpickle.dumps(s)
        print(j)
        
        s2 = jsonpickle.loads(j)
        j2 = jsonpickle.dumps(s2)
        print(j2)

        assert j == j2

        assert np.array_equal(s.container_offset, s2.container_offset)

    def test_file(self):
        filename = "dos_sd_test1.atr"
        pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
        container = load(pathname)
        container.guess_media_type()
        container.guess_filesystem()
        j = jsonpickle.dumps(container)
        print(j)
        
        c = jsonpickle.loads(j)
        j2 = jsonpickle.dumps(c)
        print(j2)

        assert j == j2
        print(c.segments)

    @pytest.mark.parametrize("filename", ["dos_sd_test1.atr", "dos_ed_test1.atr", "dos_dd_test1.atr", "dos33_master.dsk"])
    def test_file_with_filesytem(self, filename):
        pathname = os.path.join(os.path.dirname(__file__), "../samples", filename)
        container = load(pathname)
        container.guess_media_type()
        container.guess_filesystem()
        j = jsonpickle.dumps(container)
        print(j)
        
        c = jsonpickle.loads(j)
        j2 = jsonpickle.dumps(c)
        print(j2)

        assert j == j2
        print(c.segments)

if __name__ == "__main__":
    t = TestJsonPickle()
    t.setup()
    # t.test_simple_container()
    # t.test_simple_segment()
    # t.test_ordered_segment()
    # t.test_sparse_segment()
    t.test_file()
    # t.test_file_with_filesytem("dos33_master.dsk")
    # t.test_file_with_filesytem("dos_sd_test1.atr")
