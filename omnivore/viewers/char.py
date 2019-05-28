import os
import sys

import wx
import numpy as np

from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable
from ..arch.fonts import AnticFont, valid_fonts
from atrip.char_mapping import valid_font_mappings
from ..arch.font_renderers import valid_font_renderers
from .antic import AnticColorViewer

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
        array = parent.font_renderer.get_image(v, v.antic_font, data, style, start, end, end, nr, start, end)
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

        array = grid_control.font_renderer.get_image(grid_control.segment_viewer, grid_control.segment_viewer.antic_font, data, style, first_index, last_index, bytes_per_row, nr, first_col, nc)
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
        return self.segment_viewer.font_renderer

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

    def start_editing(self, evt):
        c = evt.GetKeyCode()
        print(f"start_editing: {c} for {self}")
        if c != wx.WXK_NONE:
            c = self.segment_viewer.font_mapping.convert_byte_mapping(c)
            self.process_edit(c| self.inverse)


class CharViewer(AnticColorViewer):
    name = "char"

    ui_name = "Character"

    control_cls = CharGridControl

    has_font = True

    has_width = True

    width_text = "width in characters"

    has_zoom = True

    zoom_text = "character zoom factor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._antic_font = None
        self._antic_font_uuid = "e46c1a08-b718-de27-3303-6e2701f0b0b3"  # atari800 default font
        self._antic_font_data = None
        self._font_renderer_name = "Antic 2 (Gr 0)"
        self._font_renderer = None
        self._font_mapping_name = "ASCII Order"
        self._font_mapping = None

    @property
    def window_title(self):
        return self.font_renderer_name + ", " + self.font_mapping_name + ", " + self.color_standard_name

    #### Fonts

    @property
    def font_mapping_name(self):
        return self._font_mapping_name

    @font_mapping_name.setter
    def font_mapping_name(self, value):
        self._font_mapping_name = value
        self._font_mapping = None
        self.graphics_properties_changed()

    @property
    def font_mapping(self):
        if self._font_mapping is None:
            self._font_mapping = valid_font_mappings[self._font_mapping_name]
        return self._font_mapping

    @property
    def font_renderer_name(self):
        return self._font_renderer_name

    @font_renderer_name.setter
    def font_renderer_name(self, value):
        self._font_renderer_name = value
        self._font_renderer = None
        self.graphics_properties_changed()

    @property
    def font_renderer(self):
        if self._font_renderer is None:
            self._font_renderer = valid_font_renderers[self._font_renderer_name]
        return self._font_renderer

    @property
    def antic_font(self):
        if self._antic_font is None:
            self._antic_font = AnticFont(self, self.antic_font_data, self.font_renderer, self.antic_color_registers[4:9])
        return self._antic_font

    @property
    def antic_font_uuid(self):
        return self._antic_font_uuid

    @antic_font_uuid.setter
    def antic_font_uuid(self, value):
        self._antic_font_uuid = value
        self._antic_font_data = None
        self._antic_font = None
        self.graphics_properties_changed()

    @property
    def antic_font_data(self):
        if self._antic_font_data is None:
            self._antic_font_data = valid_fonts[self._antic_font_uuid]
        return self._antic_font_data

    @antic_font_data.setter
    def antic_font_data(self, value):
        self._antic_font_uuid = value["uuid"]
        self._antic_font_data = value
        self._antic_font = None
        self.graphics_properties_changed()

    def colors_changed(self):
        """Hook for subclasses that need to invalidate stuff when colors change
        """
        self._antic_font = None
