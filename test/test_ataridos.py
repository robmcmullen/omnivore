from mock import *

from atrcopy import SegmentData, AtariDosFile, InvalidBinaryFile


class TestAtariDosFile(object):
    def setup(self):
        pass

    def test_segment(self):
        bytes = [0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2]
        rawdata = SegmentData(bytes)
        image = AtariDosFile(rawdata)
        image.parse_segments()
        assert len(image.segments) == 1
        assert len(image.segments[0]) == 2

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
        with pytest.raises(InvalidBinaryFile):
            image.parse_segments()


if __name__ == "__main__":
    t = TestAtariDosFile()
    t.setup()
    t.test_segment()
