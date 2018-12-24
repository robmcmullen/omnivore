import os
import itertools

import numpy as np
import pytest

from mock import MockEditor

import omnivore.arch.colors as colors


class TestAnticColors(object):
    def setup(self):
        self.antic_colors = colors.powerup_colors()
        self.rgb = colors.calc_playfield_rgb(self.antic_colors)
        self.highlight_rgb = colors.calc_blended_rgb(self.rgb, colors.highlight_background_rgb)
        self.data_rgb = colors.calc_dimmed_rgb(self.rgb, colors.background_rgb, colors.data_background_rgb)

    def test_simple(self):
        assert self.antic_colors[0] == 4
        assert np.array_equal(self.rgb[0], [0xf, 0xf, 0xf])
        assert np.array_equal(self.highlight_rgb[0], [0x59, 0xb0, 0xcb])
        assert np.array_equal(self.data_rgb[0], [0, 0, 0])
        assert self.antic_colors[1] == 30
        assert np.array_equal(self.rgb[1], [0xba, 0x8c, 0x2b])
        assert np.array_equal(self.highlight_rgb[1], [0x6e, 0xc0, 0xce])
        assert np.array_equal(self.data_rgb[1], [0x9b, 0x6d, 0xc])
        assert self.antic_colors[4] == 40
        assert np.array_equal(self.rgb[4], [0xb7, 0x4c, 0x66])
        assert np.array_equal(self.highlight_rgb[4], [0x6e, 0xb8, 0xd6])
        assert np.array_equal(self.data_rgb[4], [0x98, 0x2d, 0x47])
 

if __name__ == "__main__":
    t = TestAnticColors()
    t.setup()
    print(t.rgb[0:32])
    print(t.highlight_rgb[0:32])
    print(t.data_rgb[0:32])