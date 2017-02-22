import numpy as np

from mock import *

from atrcopy import SegmentData, AtariDosDiskImage, InvalidBinaryFile
from atrcopy.errors import *


class TestAtariDosSDImage(object):
    def setup(self):
        data = np.fromfile("../test_data/dos_sd_test1.atr", dtype=np.uint8)
        rawdata = SegmentData(data)
        self.image = AtariDosDiskImage(rawdata)

    def check_entries(self, entries, save_image_name=None):
        orig_num_files = len(self.image.files)
        count = 1
        for data in entries:
            filename = "TEST%d.BIN" % count
            self.image.write_file(filename, None, data)
            assert len(self.image.files) == orig_num_files + count
            data2 = self.image.find_file(filename)
            assert data.tostring() == data2
            count += 1

        # loop over them again to make sure data wasn't overwritten
        count = 1
        for data in entries:
            filename = "TEST%d.BIN" % count
            data2 = self.image.find_file(filename)
            assert data.tostring() == data2
            count += 1

        if save_image_name is not None:
            self.image.save(save_image_name)

    def test_small(self):
        assert len(self.image.files) == 5

        data = np.asarray([0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2], dtype=np.uint8)
        self.image.write_file("TEST.XEX", None, data)
        assert len(self.image.files) == 6

        data2 = self.image.find_file("TEST.XEX")
        assert data.tostring() == data2

    def test_50k(self):
        assert len(self.image.files) == 5

        data = np.arange(50*1024, dtype=np.uint8)
        self.image.write_file("RAMP50K.BIN", None, data)
        assert len(self.image.files) == 6

        data2 = self.image.find_file("RAMP50K.BIN")
        assert data.tostring() == data2

    def test_many_small(self):
        entries = [
            np.asarray([0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2], dtype=np.uint8),
            np.arange(1*1024, dtype=np.uint8),
            np.arange(2*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(4*1024, dtype=np.uint8),
            np.arange(5*1024, dtype=np.uint8),
            np.arange(6*1024, dtype=np.uint8),
            np.arange(7*1024, dtype=np.uint8),
            np.arange(8*1024, dtype=np.uint8),
            np.arange(9*1024, dtype=np.uint8),
            np.arange(10*1024, dtype=np.uint8),
            ]
        self.check_entries(entries, "many_small.atr")

    def test_big_failure(self):
        assert len(self.image.files) == 5

        data = np.arange(50*1024, dtype=np.uint8)
        self.image.write_file("RAMP50K.BIN", None, data)
        assert len(self.image.files) == 6
        with pytest.raises(NotEnoughSpaceOnDisk):
            self.image.write_file("RAMP50K2.BIN", None, data)
        assert len(self.image.files) == 6


if __name__ == "__main__":
    t = TestAtariDosFile()
    t.setup()
    t.test_segment()
