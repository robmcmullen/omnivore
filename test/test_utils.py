from builtins import object
from mock import *
from atrcopy import utils


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
