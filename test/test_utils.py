from builtins import object
from mock import *
from atrip import utils


class TestTextToInt:
    def setup(self):
        pass

    @pytest.mark.parametrize("text,expected,default_base", [
        ("12", 0x12, "hex"),
        ("$1234", 0x1234, "hex"),
        ("0xffff", 0xffff, "hex"),
        ("#12", 12, "hex"),
        ("%11001010", 202, "hex"),

        ("12", 12, "dec"),
        ("$1234", 0x1234, "dec"),
        ("0xffff", 0xffff, "dec"),
        ("#12", 12, "dec"),
        ("%11001010", 202, "dec"),
        ])
    def test_text_to_int(self, text, expected, default_base):
        assert expected == utils.text_to_int(text, default_base)

class TestRanges:
    def setup(self):
        pass

    def test_normal(self):
        values = [0, 1, 2, 3, 4, 5, 7, 10, 11, 99, 500, 501, 502, 892]
        ranges = utils.collapse_to_ranges(values)
        print(ranges)
        assert ranges == [[0, 6], [7, 8], [10, 12], [99, 100], [500, 503], [892, 893]]


    def test_compact(self):
        values = [0, 1, 2, 3, 4, 5, 7, 10, 11, 99, 500, 501, 502, 892]
        ranges = utils.collapse_to_ranges(values, True)
        print(ranges)
        assert ranges == [[0, 6], 7, [10, 12], 99, [500, 503], 892]


if __name__ == "__main__":
    t = TestRanges()
    t.setup()
    t.test_normal()
    t.test_compact()
