from __future__ import print_function
from builtins import object
import numpy as np

from mock import *

from atrcopy import SegmentData, AtariDosDiskImage, Dos33DiskImage, DefaultSegment
from atrcopy import errors


def get_image(file_name, diskimage_type):
    data = np.fromfile(file_name, dtype=np.uint8)
    rawdata = SegmentData(data)
    image = diskimage_type(rawdata)
    return image


class BaseCreateTest:
    diskimage_type = None

    def get_exe_segments(self):
        data1 = np.arange(4096, dtype=np.uint8)
        data1[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        data2 = np.arange(4096, dtype=np.uint8)
        data2[0::4] = np.repeat(np.arange(8, dtype=np.uint8), 128)
        raw = [
            (data1, 0x4000),
            (data2, 0x8000),
        ]

        segments = []
        for data, origin in raw:
            rawdata = SegmentData(data)
            s = DefaultSegment(rawdata, origin)
            segments.append(s)
        return segments

    def check_exe(self, sample_file, diskimage_type, run_addr, expected):
        image = get_image(sample_file, diskimage_type)
        segments = self.get_exe_segments()
        try:
            _ = issubclass(errors.AtrError, expected)
            with pytest.raises(errors.InvalidBinaryFile) as e:
                file_data, filetype = image.create_executable_file_image(segments, run_addr)
        except TypeError:
            file_data, filetype = image.create_executable_file_image(segments, run_addr)
            print(image)
            print(file_data, filetype)
            assert len(file_data) == expected

@pytest.mark.parametrize("sample_file", ["../test_data/dos_sd_test1.atr"])
class TestAtariDosSDImage(BaseCreateTest):
    diskimage_type = AtariDosDiskImage

    @pytest.mark.parametrize("run_addr,expected", [
        (0x2000, errors.InvalidBinaryFile),
        (None, (2 + 6 + (4 + 0x1000) + (4 + 0x1000))),
        (0x4000, (2 + 6 + (4 + 0x1000) + (4 + 0x1000))),
        (0x8000, (2 + 6 + (4 + 0x1000) + (4 + 0x1000))),
        (0xffff, errors.InvalidBinaryFile),
        ])
    def test_exe(self, run_addr, expected, sample_file):
        self.check_exe(sample_file, self.diskimage_type, run_addr, expected)


@pytest.mark.parametrize("sample_file", ["../test_data/dos33_master.dsk"])
class TestDos33Image(BaseCreateTest):
    diskimage_type = Dos33DiskImage

    @pytest.mark.parametrize("run_addr,expected", [
        (0x2000, errors.InvalidBinaryFile),
        (None, (4 + (0x9000 - 0x4000))),
        (0x4000, (4 + (0x9000 - 0x4000))),
        (0x8000, (4 + 3 + (0x9000 - 0x4000))),
        (0xffff, errors.InvalidBinaryFile),
        ])
    def test_exe(self, run_addr, expected, sample_file):
        self.check_exe(sample_file, self.diskimage_type, run_addr, expected)


if __name__ == "__main__":
    t = TestAtariDosSDImage()
    t.setup()
    t.test_exe()
