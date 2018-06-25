from __future__ import print_function
from builtins import object
from mock import *

from atrcopy import SegmentData, AtariDosFile, DefaultSegment, XexContainerSegment, errors



class TestAtariDosFile:
    def setup(self):
        pass

    def test_segment(self):
        bytes = np.asarray([0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2], dtype=np.uint8)
        rawdata = SegmentData(bytes)
        container = XexContainerSegment(rawdata, 0)
        image = AtariDosFile(container.rawdata)
        image.parse_segments()
        print(image.segments)
        assert len(image.segments) == 1
        assert len(image.segments[0]) == 2
        assert np.all(image.segments[0] == bytes[6:8])
        container.resize(16)
        for s in image.segments:
            s.replace_data(container)
        new_segment = DefaultSegment(rawdata[8:16])
        new_segment[:] = 99
        assert np.all(image.segments[0] == bytes[6:8])
        print(new_segment[:])
        assert np.all(new_segment[:] == 99)


    def test_short_segment(self):
        bytes = [0xff, 0xff, 0x00, 0x60, 0xff, 0x60, 1, 2]
        rawdata = SegmentData(bytes)
        image = AtariDosFile(rawdata)
        image.parse_segments()
        assert len(image.segments) == 1
        assert len(image.segments[0]) == 2

    def test_err_segment(self):
        bytes = [0xff, 0xff, 0x00, 0x60, 0x00, 0x00, 1, 2]
        rawdata = SegmentData(bytes)
        image = AtariDosFile(rawdata)
        with pytest.raises(errors.InvalidBinaryFile):
            image.parse_segments()


if __name__ == "__main__":
    t = TestAtariDosFile()
    t.setup()
    t.test_segment()
