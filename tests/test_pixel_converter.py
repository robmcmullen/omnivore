import os
import itertools

import numpy as np
import pytest

from mock import MockEditor

from atrcopy import SegmentData, DefaultSegment, user_bit_mask

import omnivore.arch.pixel_converters as pc


class TestBasicConverter(object):
    def setup(self):
        data = np.arange(1024, dtype=np.uint8)
        style = np.zeros(1024, dtype=np.uint8)
        raw = SegmentData(data, style)
        segment = DefaultSegment(raw, 0)
        self.editor = MockEditor(segment=segment)

    @pytest.mark.parametrize("bits_per_pixel,pixels_per_row", [
        (1,128),
        (1,64),
        (2,128),
        (2,64),
        (4,128),
        (4,64),
        (8,128),
        (8,64),
        ])
    def test_simple(self, bits_per_pixel, pixels_per_row):
        s = self.editor.segment
        if bits_per_pixel == 1:
            c = pc.Converter1bpp()
        elif bits_per_pixel == 2:
            c = pc.Converter2bpp()
        elif bits_per_pixel == 4:
            c = pc.Converter4bpp()
        elif bits_per_pixel == 8:
            c = pc.Converter8bpp()
        else:
            raise RuntimeError(f"Invalid bits_per_pixel {bits_per_pixel}")

        bytes_per_row = pixels_per_row // c.pixels_per_byte
        grid_height = s.data.shape[0] // bytes_per_row

        assert c.validate_pixels_per_row(pixels_per_row) == pixels_per_row
        assert bytes_per_row == c.calc_bytes_per_row(pixels_per_row)
        assert grid_height == c.calc_grid_height(len(s), bytes_per_row)

        grid_color_indexes, grid_style = c.calc_color_index_grid(s.data, s.style, bytes_per_row)
        assert grid_color_indexes.shape == grid_style.shape
        assert grid_color_indexes.shape == (pixels_per_row, grid_height)


if __name__ == "__main__":
    t = TestBasicConverter()
    t.setup()
    t.test_simple()
