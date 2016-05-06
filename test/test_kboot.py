import os

import numpy as np

from atrcopy import SegmentData, KBootImage, add_xexboot_header


class TestKbootHeader(object):
    def setup(self):
        pass

    def check_size(self, data):
        xex_size = len(data)
        bytes = add_xexboot_header(data)
        rawdata = SegmentData(bytes)
        size = len(rawdata)
        atr = KBootImage(rawdata)
        atr.rebuild_header()
        header_data = atr.header.to_array()
        print header_data
        newdata = np.append(header_data, atr.bytes)
        newrawdata = SegmentData(newdata)
        atr = KBootImage(newrawdata)
        atr.rebuild_header()
        image = atr.bytes
        print image[0:16]
        paragraphs = size / 16
        print atr.header, paragraphs
        assert int(image[2:4].view(dtype='<u2')) == paragraphs
        assert int(image[16 + 9:16 + 9 + 2].view('<u2')) == xex_size
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
