import os

import pytest

import numpy as np

from atrip import errors
from atrip.stringifier import find_stringifier_by_name

stringifiers = [
    ('repr', "\\x00\\x01"),
    ('hexify', "00 01 02 03"),
    ('c_bytes', "0x00,0x01,0x02,0x03"),
    ('basic_data', "DATA 0,1,2,3"),
]

class TestStringifier:
    def setup(self):
        data = np.arange(128, dtype=np.uint8)
        self.byte_data = data.tobytes()

    @pytest.mark.parametrize("name,text_check", stringifiers)
    def test_stringifier(self, name, text_check):
        s = find_stringifier_by_name(name)

        text = s.calc_text(self.byte_data)
        print(text)
        assert text != self.byte_data
        c = len(text_check)
        assert text[0:c] == text_check

        with pytest.raises(errors.UnsupportedAlgorithm):
            parsed = s.calc_byte_data(text)
            print(len(self.byte_data), len(parsed))
            assert parsed == self.byte_data

if __name__ == "__main__":
    t = TestStringifier()
    t.setup()
    t.test_stringifier('hexify', "00 01")
    t.test_stringifier('basic_data', "DATA 0,1,2")
    t.test_stringifier('repr', '\\x00\\x01')
    t.test_stringifier('c_bytes', "0x00,0x01,0x02,0x03")
