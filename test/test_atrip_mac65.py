import os

import numpy as np
import pytest

from atrip.assemblers import mac65

class TestMac65:
    def setup(self):
        self.mac65 = mac65.MAC65(True)

    @pytest.mark.parametrize(("pathname"), ["../README.rst", "test_data/fails.m65"])
    def test_failures(self, pathname):
        asm = self.mac65.assemble(pathname)
        assert not asm

    def test_lasers(self):
        asm = self.mac65.assemble("../samples/lasers.s")
        assert asm
        assert "pewpew" in asm.labels

    def test_works(self):
        asm = self.mac65.assemble("test_data/works.m65")
        assert asm
        assert "begin" in asm.labels

    def test_parse_lst(self):
        c = self.mac65
        result = mac65.AssemblerResult()
        with open("../samples/lasers.s.lst") as fh:
            text = fh.read()
        c.verbose = True
        c.parse(result, text)
        print(result.labels)
        print(result.addr_to_label)


if __name__ == "__main__":
    t = TestMac65()
    t.setup()
    t.test_parse_lst()
