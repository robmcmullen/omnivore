import os
import sys

import numpy as np

import wx

from atrip import style_bits

from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from ..viewer import SegmentViewer
from . import bitmap as b
from ..arch import pixel_converters as px
from ..arch import colors

import logging
log = logging.getLogger(__name__)


class PixelLineRenderer(b.BitmapLineRenderer):
    """The difference between this and the normal bitmap renderer is this one
    is selectable on the pixel level, rather than the byte level. Since the
    data is stored in bytes, the column range calculations are different.

    The desired column range might start and/or end at a pixel in the middle of
    a byte, so the ranges and drawing rectangles must be expanded to byte
    boundaries.
    """
    def calc_cell_size_in_pixels(self, grid_control):
        w = grid_control.zoom_w
        h = grid_control.zoom_h
        return w, h

    def col_to_rect(self, line_num, col):
        cell = self._col_to_cell[col]
        x, y = self.cell_to_pixel(line_num, cell)
        w = self.pixel_widths[col]
        rect = wx.Rect(x, y, w, self.h)
        return rect

    def calc_column_range(self, parent, line_num, first_byte, last_byte):
        t = parent.table
        row_start = (line_num * t.bytes_per_row) - t.start_offset
        index = row_start + first_byte
        if index < 0:
            first_byte -= index
            index = 0
        last_index = row_start + last_byte
        if last_index > t.last_valid_index:
            last_index = t.last_valid_index
        if index >= last_index:
            raise IndexError("No items in this line are in the visible scrolled region")
        return first_byte, index, last_index

    # BaseLineRenderer interface

    def draw_line(self, grid_control, dc, line_num, first_byte, index, last_index):
        t = grid_control.table
        rect = self.col_to_rect(line_num, first_byte * t.pixels_per_byte)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(grid_control, dc, rect, data, style)

    def add_rectangular_selection(self, caret, style_per_pixel, t, first_row, last_row, first_byte, last_byte):
        # some part of selection is visible
        start_row = max(caret.anchor_start[0] - first_row, 0)
        first_col = first_byte * t.pixels_per_byte
        left_col = max(caret.anchor_start[1] - first_col, 0)
        last_col = last_byte * t.pixels_per_byte
        right_col = min(caret.anchor_end[1] - first_col + 1, last_col - first_col + 1)
        end_row = min(caret.anchor_end[0] - first_row + 1, last_row - first_row + 1)
        s2d = style_per_pixel.reshape((-1, (last_byte - first_byte) * style_per_pixel.shape[-1]))
        print("OETUSHNTOEHUSROEHU rectangular selection", start_row, left_col, end_row, right_col, style_per_pixel.shape, s2d.shape)
        s2d[start_row:end_row, left_col:right_col] |= style_bits.selected_bit_mask

    def draw_grid(self, grid_control, dc, first_row, visible_rows, first_cell, visible_cells):
        t = grid_control.table
        t.prepare_for_drawing(first_row, visible_rows, first_cell, visible_cells)
        last_cell = min(first_cell + visible_cells, self.num_cells)
        last_row = min(first_row + visible_rows, t.num_rows)
        log.debug("draw_grid: rows:%d,%d (vis %d, num %d) cols:%d,%d" % (first_row, last_row, visible_rows, t.num_rows, first_cell, last_cell))

        ul_rect = self.col_to_rect(first_row, first_cell)
        lr_rect = self.col_to_rect(last_row - 1, last_cell - 1)
        frame_rect = wx.Rect(ul_rect.x, ul_rect.y, lr_rect.x - ul_rect.x + lr_rect.width, lr_rect.y - ul_rect.y + lr_rect.height)
        dc.SetClippingRegion(frame_rect)
 
        pixels, style = t.current_rectangle
        pixels = pixels[:,first_cell:last_cell]
        style = style[:,first_cell:last_cell]
        array = px.calc_rgb_from_color_indexes(pixels, style, grid_control.color_list_rgb, grid_control.empty_color_rgb)
        width = array.shape[1]
        height = array.shape[0]
        print(f"array: {array.shape}")
        if width > 0 and height > 0:
            array = intscale(array, grid_control.zoom_h, grid_control.zoom_w)
                #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tobytes())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, frame_rect.x, frame_rect.y)


class PixelTable(cg.HexTable):
    def __init__(self, control, linked_base):
        self.control = control
        s = self.segment
        self.num_rows = self.converter.calc_grid_height(len(s.data), self.control.bytes_per_row)
        cg.HexTable.__init__(self, s.data, s.style, self.control.items_per_row, self.segment.origin)

    @property
    def segment(self):
        return self.control.segment_viewer.linked_base.segment

    @property
    def converter(self):
        return self.control.pixel_converter

    @property
    def indexes_per_row(self):
        return self.control.bytes_per_row

    def calc_num_rows(self):
        return self.num_rows

    def calc_last_valid_index(self):
        return self.indexes_per_row * self.num_rows

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        """Create an array of color index values that contains the visible
        portion of the pixel array

        The array created here is actually bigger than the visible array, as
        wide as the entire set of data, but only as tall as the visible area.
        """
        # cells and columns are equivalent in pixel grids
        s = self.segment
        bytes_per_row = self.control.bytes_per_row
        start_index = start_row * bytes_per_row
        last_index = (start_row + visible_rows) * bytes_per_row
        last_valid = len(s.data)
        if last_index > last_valid:
            total_count = last_index - start_index
            valid_count = last_valid - start_index
            byte_values = np.empty(total_count, dtype=np.uint8)
            byte_values[:valid_count] = s.data[start_index:last_valid]
            byte_values[valid_count:] = 0
            style_values = np.empty(total_count, dtype=np.uint8)
            style_values[:valid_count] = s.style[start_index:last_index]
            style_values[valid_count:] = px.invalid_style
        else:
            byte_values = s.data[start_index:last_index]
            style_values = s.style[start_index:last_index]
        self.current_rectangle = self.converter.calc_color_index_grid(byte_values, style_values, bytes_per_row)

    def rebuild(self):
        segment = self.control.segment_viewer.segment
        self.current_rectangle = None
        self.num_rows = self.converter.calc_grid_height(len(s.data), self.control.bytes_per_row)
        print(f"new num_rows: {self.num_rows}")


class PixelGridControl(SegmentGridControl):
    default_table_cls = PixelTable

    def set_viewer_defaults(self):
        self.bytes_per_row = 16
        self.items_per_row = 8  # 1 byte per pixel fallback
        self.zoom = 2

        self.antic_colors = colors.powerup_colors()
        rgb = colors.calc_playfield_rgb(self.antic_colors)
        highlight_rgb = colors.calc_blended_rgb(rgb, colors.highlight_background_rgb)
        match_rgb = colors.calc_blended_rgb(rgb, colors.match_background_rgb)
        comment_rgb = colors.calc_blended_rgb(rgb, colors.comment_background_rgb)
        data_rgb = colors.calc_dimmed_rgb(rgb, colors.background_rgb, colors.data_background_rgb)
        self.color_list_rgb = (rgb, highlight_rgb, match_rgb, comment_rgb, data_rgb)
        self.empty_color_rgb = colors.empty_background_rgb

    @property
    def pixel_converter(self):
        return self.segment_viewer.pixel_converter

    @property
    def zoom_w(self):
        return self.zoom * self.pixel_converter.scale_width

    @property
    def zoom_h(self):
        return self.zoom * self.pixel_converter.scale_height

    @property
    def pixels_per_byte(self):
        return self.pixel_converter.pixels_per_byte

    @property
    def scale_width(self):
        return self.pixel_converter.scale_width

    @property
    def scale_height(self):
        return self.pixel_converter.scale_height

    def calc_default_table(self, linked_base):
        if hasattr(self, 'segment_viewer'):
            self.items_per_row = self.pixel_converter.validate_pixels_per_row(self.items_per_row)
            self.bytes_per_row = self.pixel_converter.calc_bytes_per_row(self.items_per_row)
            return self.default_table_cls(self, linked_base)
        return SegmentTable(linked_base, self.bytes_per_row)

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            self.items_per_row = self.bytes_per_row * self.pixels_per_byte
            return PixelLineRenderer(self)
        return SegmentGridControl.calc_line_renderer(self)

    def verify_line_renderer(self):
        self.recalc_line_renderer()


class PixelViewer(SegmentViewer):
    name = "pixel"

    ui_name = "Pixel Array"

    control_cls = PixelGridControl

    has_bitmap = True

    has_colors = True

    has_width = True

    width_text = "bitmap width in pixels"

    has_zoom = True

    zoom_text = "bitmap zoom factor"


    def __init__(self, *args, **kwargs):
        SegmentViewer.__init__(self, *args, **kwargs)
        self.pixel_converter = px.AnticE()

    @property
    def window_title(self):
        return "Pixels: " + self.pixel_converter.ui_name

    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    def validate_width(self, width):
        return width

    def recalc_data_model(self):
        self.control.recalc_view()
