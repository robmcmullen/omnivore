import os
import itertools

import numpy as np
import pytest

from mock import MockEditor

from atrcopy import SegmentData, DefaultSegment, user_bit_mask

import omnivore.arch.pixel_converters as pc
import omnivore.arch.pixel_speedups as fast_pc
import omnivore.arch.colors as colors

antic_colors = colors.powerup_colors()
rgb = colors.calc_playfield_rgb(antic_colors)
highlight_rgb = colors.calc_blended_rgb(rgb, colors.highlight_background_rgb)
match_rgb = colors.calc_blended_rgb(rgb, colors.match_background_rgb)
comment_rgb = colors.calc_blended_rgb(rgb, colors.comment_background_rgb)
data_rgb = colors.calc_dimmed_rgb(rgb, colors.background_rgb, colors.data_background_rgb)
color_list = (rgb, highlight_rgb, match_rgb, comment_rgb, data_rgb)
empty_rgb = colors.empty_background_rgb

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
        assert grid_color_indexes.shape == (grid_height, pixels_per_row)

        rgb_image = pc.calc_rgb_from_color_indexes_python(grid_color_indexes, grid_style, color_list, empty_rgb)
        assert rgb_image.shape == (grid_height, pixels_per_row, 3)

        fast_rgb_image = fast_pc.calc_rgb_from_color_indexes(grid_color_indexes, grid_style, color_list, empty_rgb)
        assert(np.array_equal(rgb_image, fast_rgb_image))


if __name__ == "__main__":
    data = np.arange(64, dtype=np.uint8)
    style = np.zeros(64, dtype=np.uint8)
    raw = SegmentData(data, style)
    segment = DefaultSegment(raw, 0)
    print(data)

    ppb = 8
    pixels_per_row = 16
    bytes_per_row = pixels_per_row // ppb
    c = pc.Converter1bpp()
    grid_color_indexes, grid_style = c.calc_color_index_grid(data, style, bytes_per_row)
    print(grid_color_indexes)

    ppb = 4
    pixels_per_row = 16
    bytes_per_row = pixels_per_row // ppb
    c = pc.Converter2bpp()
    grid_color_indexes, grid_style = c.calc_color_index_grid(data, style, bytes_per_row)
    print(grid_color_indexes)

    # ppb = 2
    # pixels_per_row = 16
    # bytes_per_row = pixels_per_row // ppb
    # c = pc.Converter4bpp()
    # grid_color_indexes, grid_style = c.calc_color_index_grid(data, style, bytes_per_row)
    # print(grid_color_indexes)

    # ppb = 1
    # pixels_per_row = 16
    # bytes_per_row = pixels_per_row // ppb
    # c = pc.Converter8bpp()
    # grid_color_indexes, grid_style = c.calc_color_index_grid(data, style, bytes_per_row)
    # print(grid_color_indexes)

    rgb_image = pc.calc_rgb_from_color_indexes(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    print(rgb_image)

    print(color_list)
    fast_rgb_image = fast_pc.calc_rgb_from_color_indexes(grid_color_indexes, grid_style, color_list, empty_rgb)
    print(fast_rgb_image)

    assert(np.array_equal(rgb_image, fast_rgb_image))

    import timeit
    def call_pure_python():
        pc.calc_rgb_from_color_indexes_python(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    duration = timeit.timeit(call_pure_python, number=1000)
    print(duration)

    def call_naive_cython():
        fast_pc.calc_rgb_from_color_indexes_naive(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    duration = timeit.timeit(call_naive_cython, number=1000)
    print(duration)

    def call_better_cython():
        fast_pc.calc_rgb_from_color_indexes_better(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    duration = timeit.timeit(call_better_cython, number=1000)
    print(duration)

    def call_fast():
        fast_pc.calc_rgb_from_color_indexes_fast(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    duration = timeit.timeit(call_fast, number=1000)
    print(duration)

    def call_fast_optimize():
        fast_pc.calc_rgb_from_color_indexes_fast_optimize(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    duration = timeit.timeit(call_fast, number=1000)
    print(duration)

    def call_fast_final():
        fast_pc.calc_rgb_from_color_indexes_fast(grid_color_indexes, grid_style, color_list, colors.empty_background_rgb)
    duration = timeit.timeit(call_fast_final, number=1000)
    print(duration)
