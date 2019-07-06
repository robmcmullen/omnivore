import os

import numpy as np
import pytest

from atrip.assemblers.mac65 import MAC65

class TestMac65:
    def setup(self):
        self.mac65 = MAC65()

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
