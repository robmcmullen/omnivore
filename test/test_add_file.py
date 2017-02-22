import numpy as np

from mock import *

from atrcopy import SegmentData, AtariDosDiskImage, InvalidBinaryFile


class TestAtariDosSDImage(object):
    def setup(self):
        data = np.fromfile("../test_data/dos_sd_test1.atr", dtype=np.uint8)
        rawdata = SegmentData(data)
        self.image = AtariDosDiskImage(rawdata)

    def test_small(self):
        assert len(self.image.files) == 5

        data = [0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2]
        self.image.write_file("TEST.XEX", None, data)
        assert len(self.image.files) == 6


if __name__ == "__main__":
    t = TestAtariDosFile()
    t.setup()
    t.test_segment()
