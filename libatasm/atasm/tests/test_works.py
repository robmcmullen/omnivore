import os

from mock import *

from pyatasm import Assemble


class TestBasic(object):
    def setup(self):
        self.items = [
                         ("works.m65", [
                            (1536, 1688, 50),
                            ],
                            ),

                     ]

    def test_simple(self):
        for filename, results in self.items:
            asm = Assemble(filename)
            assert len(asm.segments) == len(results)

if __name__ == "__main__":
    t = TestBasic()
    t.setup()
    t.test_simple()
