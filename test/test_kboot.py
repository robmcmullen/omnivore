import os

import numpy as np

from atrcopy import KBootImage, add_kboot_header


class TestKbootHeader(object):
    def setup(self):
        pass

    def check_size(self, data):
        size = np.alen(data)
        image = add_kboot_header(data)
        assert int(image[2:4].view(dtype='<u2')) == ((size + 127) / 128) * 128 / 16
        assert int(image[16 + 9:16 + 9 + 2].view('<u2')) == size
        return image

    def test_simple(self):
        for size in range(2000, 40000, 1000):
            data = np.arange(size, dtype=np.uint8)
            self.check_size(data)
    
    def test_real(self):
        data = np.fromfile("air_defense_v18.xex", dtype=np.uint8)
        image = self.check_size(data)
        with open("air_defense_v18.atr", "wb") as fh:
            txt = image.tostring()
            fh.write(txt)

if __name__ == "__main__":
    t = TestKbootHeader()
    t.setup()
    t.test_simple()
    t.test_real()
