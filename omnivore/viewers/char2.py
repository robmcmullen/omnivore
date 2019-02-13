import os
import sys

import wx
import numpy as np

from traits.api import on_trait_change, Bool, Undefined

from omnivore_framework.utils.nputil import intscale
from omnivore_framework.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)


class AnticCharImageCache(cg.DrawTextImageCache):
    def draw_item(self, parent, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        data = data.reshape((nr, -1))
        style = style.reshape((nr, -1))
        v = parent.segment_viewer
        array = parent.font_renderer.get_image(v, v.current_antic_font, data, style, start, end, end, nr, start, end)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, parent.zoom_h, parent.zoom_w)
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tobytes())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class AnticCharRenderer(cg.TableLineRenderer):
    default_image_cache = AnticCharImageCache

    def __init__(self, parent, image_cache=None):
        image_cache = AnticCharImageCache()
        w = parent.font_renderer.char_bit_width * parent.zoom_w
        h = parent.font_renderer.char_bit_height * parent.zoom_h
        cg.LineRenderer.__init__(self, parent, w, h, parent.items_per_row, image_cache)

    # BaseLineRenderer interface

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = parent.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(parent, dc, rect, data, style)

    # fast BaseLineRenderer interface drawing entire grid at once

    def draw_grid(self, grid_control, dc, first_row, visible_rows, first_cell, visible_cells):
        t = grid_control.table
        first_col = self.cell_to_col(first_row, first_cell)
        last_cell = min(first_cell + visible_cells, self.num_cells)
        last_row = min(first_row + visible_rows, t.num_rows)
        last_col = self.cell_to_col(last_row, last_cell - 1) + 1
        log.debug("draw_grid: rows:%d,%d (vis %d, num %d) cols:%d,%d" % (first_row, last_row, visible_rows, t.num_rows, first_col, last_col))

        ul_rect = self.col_to_rect(first_row, first_col)
        lr_rect = self.col_to_rect(last_row - 1, last_col - 1)
        frame_rect = wx.Rect(ul_rect.x, ul_rect.y, lr_rect.x - ul_rect.x + lr_rect.width, lr_rect.y - ul_rect.y + lr_rect.height)
        dc.SetClippingRegion(frame_rect)

        # First and last rows may not span entire width. Process those
        # separately
        #
        # First row may not have bytes at the beginning of the row if the start
        # offset is not zero
        if first_row == 0:
            try:
                col, index, last_index = self.calc_column_range(grid_control, first_row, first_col, last_col)
            except IndexError:
                pass  # skip lines with no visible cells
            else:
                self.draw_line(grid_control, dc, first_row, col, index, last_index)
            first_row += 1
            if first_row == last_row:
                return
            frame_rect.y += ul_rect.height

        # Last row may not have bytes at the end of the row
        if last_row == t.num_rows:
            try:
                col, index, last_index = self.calc_column_range(grid_control, last_row - 1, first_col, last_col)
            except IndexError:
                pass  # skip lines with no visible cells
            else:
                self.draw_line(grid_control, dc, last_row - 1, col, index, last_index)
            last_row -= 1

        bytes_per_row = t.items_per_row
        nr = last_row - first_row
        nc = last_col - first_col
        first_index = (first_row * bytes_per_row) - t.start_offset
        last_index = (last_row * bytes_per_row) - t.start_offset
        t = t
        if last_index > len(t.data):
            last_index = len(t.data)
            data = np.zeros((nr * bytes_per_row), dtype=np.uint8)
            data[0:last_index - first_index] = t.data[first_index:last_index]
            style = np.zeros((nr * bytes_per_row), dtype=np.uint8)
            style[0:last_index - first_index] = t.style[first_index:last_index]
        else:
            data = t.data[first_index:last_index]
            style = t.style[first_index:last_index]
        data = data.reshape((nr, -1))
        style = style.reshape((nr, -1))

        # get_image(cls, machine, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):

        array = grid_control.font_renderer.get_image(grid_control.segment_viewer, grid_control.segment_viewer.current_antic_font, data, style, first_index, last_index, bytes_per_row, nr, first_col, nc)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, grid_control.zoom_h, grid_control.zoom_w)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tobytes())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, frame_rect.x, frame_rect.y)


class CharGridControl(SegmentGridControl):
    initial_zoom = 2

    def set_viewer_defaults(self):
        self.items_per_row = self.view_params.map_width
        self.zoom = 2
        self.inverse = 0

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            return AnticCharRenderer(self)
        return SegmentGridControl.calc_line_renderer(self)

    def verify_line_renderer(self):
        self.recalc_line_renderer()

    @property
    def font_renderer(self):
        return self.segment_viewer.machine.font_renderer

    @property
    def zoom_w(self):
        return self.zoom * self.font_renderer.scale_width

    @property
    def zoom_h(self):
        return self.zoom * self.font_renderer.scale_height

    def recalc_view(self):
        self.table = SegmentTable(self.segment_viewer.linked_base, self.items_per_row)
        self.line_renderer = self.calc_line_renderer()
        SegmentGridControl.recalc_view(self)

    def handle_char_ordinary(self, evt):
        c = evt.GetKeyCode()
        print(("ordinary char: %s", c))
        if c != wx.WXK_NONE:
            c = self.segment_viewer.machine.font_mapping.convert_byte_mapping(c)
            self.process_edit(c| self.inverse)


class CharViewer(SegmentViewer):
    name = "char"

    pretty_name = "Character"

    control_cls = CharGridControl

    has_font = True

    has_colors = True

    has_width = True

    width_text = "width in characters"

    has_zoom = True

    zoom_text = "character zoom factor"

    @property
    def window_title(self):
        return self.machine.font_renderer.name + ", " + self.machine.font_mapping.name + ", " + self.machine.color_standard_name

    # @on_trait_change('machine.bitmap_color_change_event')
    def update_font_colors(self, evt):
        log.debug("CharViewer: machine font colors changed for %s" % self.control)
        if evt is not Undefined:
            self.set_font()

    # @on_trait_change('machine.font_change_event')
    def update_font(self, evt):
        log.debug("CharViewer: machine font changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
