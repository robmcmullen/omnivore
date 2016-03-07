import os
import itertools

import numpy as np
import pytest

from atrcopy import DefaultSegment

from omnivore.utils.searchalgorithm import *


class MockEditor(object):
    def __init__(self, segment):
        self.segment = segment
        
class TestSearch1(object):
    def setup(self):
        data = np.arange(16, dtype=np.uint8)
        style = np.zeros(16, dtype=np.uint8)
        self.editor = MockEditor(DefaultSegment(data, style, 0))

    def test_simple(self):
        items = [
            ("a > 1", [(2, 16)]),
            ("a > $a", [(11, 16)]),
            ("a > $A", [(11, 16)]),
            ("a > 0xA", [(11, 16)]),
            ("b > 8", [(9, 16)]),
            ("(a > 3) & (a > 5)", [(6, 16)]),
            ("(a * b) > 128", [(12, 16)]),
            ("(a - b) > 0", []),
            ("(2 * a - b) > 0", [(1,16)]),
            ("(a & 7) - (b & 3) > 0", [(4, 8), (12, 16)]),
            ("a % 4 == 3", [(3, 4), (7, 8), (11, 12), (15, 16)]),
            ("((a > 0", None),  # parse error!
        ]

        for search_text, expected in items:
            if expected is None:
                with pytest.raises(ValueError) as ex:
                    s = AlgorithmSearcher(self.editor, search_text)
            else:
                s = AlgorithmSearcher(self.editor, search_text)
                print search_text, s.matches
                assert expected == s.matches

if __name__ == "__main__":
    t = TestSearch1()
    t.setup()
    t.test_simple()
