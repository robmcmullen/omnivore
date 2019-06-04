import os

import numpy as np
import pytest

from atrip.container import Container
from atrip.segment import Segment

from omnivore.utils.searchutil import HexSearcher

from mock import MockEditor


class TestFind:
    def setup(self):
        data = np.arange(4096, dtype=np.uint8)
        data[1::2] = np.repeat(np.arange(16, dtype=np.uint8), 128)
        data[::100] = 0x7f
        self.container = Container(data)
        self.segment = Segment(self.container)
        index_by_100 = np.arange(40, dtype=np.int32) * 100
        self.seg100 = Segment(self.segment, index_by_100)
        self.seg1000 = Segment(self.seg100, [0,10,20,30])
        self.editor = MockEditor(self.segment)

    def test_find_hex(self):
        search_text = "7f"
        search_copy = self.segment.tobytes()
        searcher = HexSearcher(self.editor, search_text, search_copy)
        print(search_copy)
        print(searcher.matches)
        assert len(searcher.matches) == 41


if __name__ == "__main__":
    t = TestFind()
    t.setup()
    t.test_find_hex()
